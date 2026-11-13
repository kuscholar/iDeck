/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedLibraryConfig.h"
#include "SharedSteamLibrary.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
struct token {size_t start,end;int kind,quoted;};
struct reader {const char *bytes;size_t size,pos,tokens;};
/* Token spans refer to original bytes; no reserialization of existing fields. */
static int next(struct reader *r,struct token *t) {
    for(;;) {
        while(r->pos<r->size&&(unsigned char)r->bytes[r->pos]<=32)r->pos++;
        if(r->pos+1<r->size&&r->bytes[r->pos]=='/'&&r->bytes[r->pos+1]=='/') {
            while(r->pos<r->size&&r->bytes[r->pos]!='\n')r->pos++;
        }else break;
    }
    *t=(struct token){.start=r->pos};
    if(r->pos==r->size)return 0;
    if(++r->tokens>100000)return -22;
    unsigned char ch=r->bytes[r->pos++];
    if(ch=='{'||ch=='}'){t->kind=ch;t->end=r->pos;return 1;}
    t->kind='s';t->quoted=ch=='"';
    if(t->quoted) {
        while(r->pos<r->size) {
            ch=r->bytes[r->pos++];
            if(ch=='"'){t->end=r->pos;return 1;}
            if(ch=='\\'&&r->pos<r->size&&(r->bytes[r->pos]=='"'||r->bytes[r->pos]=='\\'))r->pos++;
        }
        return -22;
    }
    while(r->pos<r->size&&(unsigned char)r->bytes[r->pos]>32&&r->bytes[r->pos]!='{'&&r->bytes[r->pos]!='}')r->pos++;
    t->end=r->pos;return 1;
}
static int value(const struct reader *r,struct token t,char *out,size_t size) {
    if(t.kind!='s'||!size)return 0;
    size_t begin=t.start+(size_t)t.quoted,end=t.end-(size_t)t.quoted,used=0;
    for(size_t i=begin;i<end;i++) {
        char ch=r->bytes[i];
        if(ch=='\\'&&i+1<end&&(r->bytes[i+1]=='"'||r->bytes[i+1]=='\\'))ch=r->bytes[++i];
        if(used+1>=size)return 0;out[used++]=ch;
    }
    out[used]=0;return 1;
}
static int equals(const struct reader *r,struct token t,const char *wanted) {
    char word[1024];return value(r,t,word,sizeof word)&&!strcmp(word,wanted);
}
static int key_equal(const struct reader *r,struct token t,const char *wanted) {
    char word[64];if(!value(r,t,word,sizeof word))return 0;
    for(size_t i=0;word[i];i++)if(word[i]>='A'&&word[i]<='Z')word[i]+='a'-'A';
    return !strcmp(word,wanted);
}
static int number(const struct reader *r,struct token t,uint32_t *out) {
    char word[32];if(!value(r,t,word,sizeof word)||!word[0])return 0;
    uint64_t n=0;for(size_t i=0;word[i];i++){if(word[i]<'0'||word[i]>'9')return 0;n=n*10+(unsigned)(word[i]-'0');if(n>2147483646)return -1;}
    *out=(uint32_t)n;return 1;
}
static int object(struct reader *r,unsigned depth,int library,int *found) {
    if(depth>=32)return -22;
    int library_found=0;
    for(;;) {
        struct token key,item;int n=next(r,&key);if(n<=0)return -22;
        if(key.kind=='}'){if(library_found)*found=1;return 0;}
        if(key.kind!='s'||next(r,&item)<=0)return -22;
        if(item.kind=='{'){if(library&&key_equal(r,key,"path"))library_found=0;int e=object(r,depth+1,0,found);if(e)return e;}
        else if(item.kind!='s')return -22;
        else if(library&&key_equal(r,key,"path"))library_found=equals(r,item,IDECK_SHARED_STEAM_GUEST);
    }
}
int ideck_shared_library_plan(const char *input,size_t size,char *output,size_t capacity,size_t *written,int *changed) {
    if(written)*written=0;if(changed)*changed=0;
    if(!output||!written||!changed||(!input&&size))return -22;
    if(size>IDECK_LIBRARY_CONFIG_MAX)return -7;
    static const char fresh[]="\"libraryfolders\"\n{\n\"0\" { \"path\" \"/Steam\" }\n\"1\" { \"path\" \"" IDECK_SHARED_STEAM_GUEST "\" \"label\" \"iDeck Madeira\" \"apps\" {} }\n}\n";
    if(!size){if(capacity<sizeof fresh-1)return -7;memcpy(output,fresh,sizeof fresh-1);*written=sizeof fresh-1;*changed=1;return 0;}
    if(memchr(input,0,size))return -22;
    struct reader r={.bytes=input,.size=size};struct token key,item;
    if(size>=3&&!memcmp(input,"\xef\xbb\xbf",3))r.pos=3;
    if(next(&r,&key)<=0||!key_equal(&r,key,"libraryfolders")||next(&r,&item)<=0||item.kind!='{')return -22;
    uint32_t largest=0;int have_number=0,found=0;size_t closing=0;
    for(;;) {
        if(next(&r,&key)<=0)return -22;
        if(key.kind=='}'){closing=key.start;break;}
        if(key.kind!='s'||next(&r,&item)<=0)return -22;
        uint32_t index=0;int numeric=number(&r,key,&index);if(numeric<0)return -22;
        if(numeric){if(!have_number||index>largest)largest=index;have_number=1;}
        if(item.kind=='{'){int e=object(&r,1,numeric,&found);if(e)return e;}
        else if(item.kind!='s')return -22;
        else if(numeric&&equals(&r,item,IDECK_SHARED_STEAM_GUEST))found=1; /* legacy flat format */
    }
    if(next(&r,&item)!=0)return -22;
    if(found)return 0;
    if(have_number&&largest==2147483646)return -22;
    char entry[256];int n=snprintf(entry,sizeof entry,"\n\"%u\" { \"path\" \"%s\" \"label\" \"iDeck Madeira\" \"apps\" {} }\n",have_number?largest+1:0,IDECK_SHARED_STEAM_GUEST);
    if(n<0||(size_t)n>=sizeof entry||size>capacity||(size_t)n>capacity-size)return -7;
    memcpy(output,input,closing);memcpy(output+closing,entry,(size_t)n);memcpy(output+closing+(size_t)n,input+closing,size-closing);
    *written=size+(size_t)n;*changed=1;return 0;
}
