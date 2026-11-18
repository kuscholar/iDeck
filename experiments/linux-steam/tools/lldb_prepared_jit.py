# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Developer-only LLDB integration for the explicitly opted-in iDeck Linux Lab.
# References the existing StikJIT1.9.0 developer preparation contract; new code.
# Never writes Valve/FEX/image code or changes entitlements/security settings.
import json,struct,time,shlex
from pathlib import Path
import lldb
LENGTH=120*1024*1024
PAGE=16384
MAGIC=0x49444a4954525831

def own_data_symbol(target,module,name):
    contexts=target.FindSymbols(name,lldb.eSymbolTypeData);addresses=set()
    for index in range(contexts.GetSize()):
        context=contexts.GetContextAtIndex(index);symbol=context.GetSymbol()
        if symbol.GetName() not in (name,'_'+name):continue
        if context.GetModule().GetUUIDString()!=module.GetUUIDString():continue
        addresses.add(symbol.GetStartAddress().GetLoadAddress(target))
    assert len(addresses)==1,('Ambiguous own native metadata symbol',name,len(addresses))
    return next(iter(addresses))

def validate_rx(process,start,length):
    cursor=start;end=start+length;steps=0
    while cursor<end:
        steps+=1;assert steps<=LENGTH//PAGE
        info=lldb.SBMemoryRegionInfo();error=process.GetMemoryRegionInfo(cursor,info)
        assert error.Success() and info.IsMapped() and info.GetRegionBase()<=cursor and info.GetRegionEnd()>cursor
        assert info.IsReadable() and info.IsExecutable() and not info.IsWritable(), 'OS did not grant a pure RX range'
        cursor=min(end,info.GetRegionEnd())
    return steps

def prepare(debugger,command,result,internal_dict):
    arguments=shlex.split(command);assert len(arguments)==1,'Pass only the private run configuration path'
    config_path=Path(arguments[0]).resolve();assert str(config_path).startswith('/Volumes/easystore/')
    config=json.loads(config_path.read_text());target=debugger.GetSelectedTarget();process=target.GetProcess();module=target.GetModuleAtIndex(0)
    assert process.IsValid() and process.GetState()==lldb.eStateStopped and process.GetProcessID()==config['pid']
    assert module.GetFileSpec().GetFilename()=='Madeira'
    assert module.GetUUIDString().replace('-','').lower()==config['image_uuid'].replace('-','').lower()
    frame=process.GetSelectedThread().GetFrameAtIndex(0)
    assert (frame.GetFunctionName() or '').split('(')[0]=='ideck_lab_native_jit_prepare_debugger'
    offer=own_data_symbol(target,module,'ideck_lab_debugger_jit_offer')
    error=lldb.SBError();initial=process.ReadMemory(offer,40,error)
    assert error.Success() and initial==bytes(40),'Offer is not fresh; preserve process'
    output=Path(config['receipt']);assert str(output).startswith('/Volumes/easystore/') and not output.exists()
    error=lldb.SBError();rx=process.AllocateMemory(LENGTH,lldb.ePermissionsReadable|lldb.ePermissionsExecutable,error)
    assert error.Success() and 0<rx<2**47 and rx%PAGE==0,'OS debugger RX allocation refused'
    completed=0;published=False;started=time.monotonic()
    try:
        before_regions=validate_rx(process,rx,LENGTH)
        for image in target.module_iter():
            for section in image.section_iter():
                address=section.GetLoadAddress(target);size=section.GetByteSize()
                if address!=lldb.LLDB_INVALID_ADDRESS and size:
                    assert not (rx<address+size and address<rx+LENGTH),'Fresh arena overlaps existing image'
        for offset in range(0,LENGTH,PAGE):
            assert time.monotonic()-started<180,'Bounded preparation deadline exceeded'
            error=lldb.SBError();written=process.WriteMemory(rx+offset,b'\x69',error)
            assert error.Success() and written==1,('OS debugger page write refused',completed,str(error))
            completed+=1
            if completed%1024==0:print('own Linux RX pages prepared',completed,'elapsed_s',round(time.monotonic()-started,2),flush=True)
        after_regions=validate_rx(process,rx,LENGTH)
        # Only native Lab metadata. Payload first, publication word last. No
        # guest input, arbitrary launch data, register edits or PC skipping.
        error=lldb.SBError();payload=struct.pack('<QQQQ',process.GetProcessID(),rx,LENGTH,completed)
        assert process.WriteMemory(offer+8,payload,error)==32 and error.Success()
        error=lldb.SBError();assert process.WriteMemory(offer,struct.pack('<Q',MAGIC),error)==8 and error.Success()
        published=True
        record={'pid':process.GetProcessID(),'image_uuid':module.GetUUIDString(),'RX_region':rx,'bytes':LENGTH,'page_bytes':PAGE,'prepared_pages':completed,'RX_segments_before':before_regions,'RX_segments_after':after_regions,'elapsed_s':time.monotonic()-started,'offer_published':True,'code_executed':False,'Linux_started':False,'Steam_UI_validated':False,'scope':'Only fresh own code arena via authorized developer debugger; native adoption/self-check and actual guest/UI still unverified'}
        output.write_text(json.dumps(record,indent=2)+'\n')
        print('Published exact single-use native offer. Remove own breakpoint and detach normally for actual self-check.',flush=True)
    except Exception as exc:
        cleaned=False
        if not published:cleaned=process.DeallocateMemory(rx).Success()
        output.write_text(json.dumps({'pid':process.GetProcessID(),'prepared_pages':completed,'offer_published':published,'unused_RX_cleaned':cleaned,'error':str(exc),'keep_process_stopped':True},indent=2)+'\n')
        raise

def __lldb_init_module(debugger,internal_dict):
    debugger.HandleCommand('command script add -f '+__name__+'.prepare ideck-prepare-linux-offer')
