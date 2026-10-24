/* VideoToolbox / AudioToolbox decoders for the wg_parser core.
 *                                                        (MADEIRA ml1990)
 *
 * WHY: a 64-bit title plays its menu video through Media Foundation's source
 * resolver.  mfmp4srcsnk.dll is not part of Wine, so the resolver falls back to
 * winegstreamer's media source, whose wg_parser (wg_parser_av_ios.c) knew only
 * MP3 and WAV and refused the MP4 -- the title then retried the open about a
 * dozen times a second and its menu, which waits for the video, never came.
 *
 * libavformat's mov demuxer now splits the MP4.  The H.264 / HEVC / AAC
 * decoding is NOT done by FFmpeg (this port builds no such decoder, see
 * build/ffmpeg/build.sh): it is done here by the platform's own decoders --
 * VideoToolbox for video (hardware, NV12 output) and an AudioToolbox
 * AudioConverter for AAC (float PCM output).
 *
 * This translation unit includes no Wine and no FFmpeg header; the contract
 * with the core is wg_parser_backend_ios.h.  It is compiled on its own by
 * build/ntdll-unix/build.sh and linked into libntdll_unix.a.
 */
#ifdef __APPLE__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <CoreFoundation/CoreFoundation.h>
#include <CoreMedia/CoreMedia.h>
#include <CoreVideo/CoreVideo.h>
#include <VideoToolbox/VideoToolbox.h>
#include <AudioToolbox/AudioToolbox.h>

#include "wg_parser_backend_ios.h"

#define MAV_MAX_PARAM_SETS 32

/***********************************************************************
 *           VideoToolbox
 */
struct vt_dec
{
    int codec;
    CMVideoFormatDescriptionRef fmt;
    VTDecompressionSessionRef session;
    /* the decode() call currently in progress */
    mav_vframe_emit emit;
    void *ctx;
    OSStatus frame_status;
};

static void vt_output( void *refcon, void *frame_refcon, OSStatus status, VTDecodeInfoFlags flags,
                       CVImageBufferRef image, CMTime pts, CMTime duration )
{
    struct vt_dec *d = refcon;

    (void)frame_refcon;
    if (status != noErr)
    {
        d->frame_status = status;
        return;
    }
    if (!image || (flags & kVTDecodeInfo_FrameDropped) || !d->emit) return;
    CVPixelBufferRetain( image );
    d->emit( d->ctx, (void *)image,
             (pts.flags & kCMTimeFlags_Valid) ? pts.value : INT64_MIN,
             (duration.flags & kCMTimeFlags_Valid) ? duration.value : INT64_MIN );
}

/* avcC: version, profile, compat, level, 0xfc|len-1, 0xe0|nSPS, {u16 len, SPS}..., nPPS, {u16 len, PPS}... */
static int parse_avcc( const uint8_t *p, uint32_t n, const uint8_t **sets, size_t *sizes, size_t *count,
                       int *nal_len, char *why, size_t why_size )
{
    uint32_t pos = 6, i, groups;

    if (n < 7 || p[0] != 1)
    {
        snprintf( why, why_size, "H.264 codec data is not avcC (%u bytes, first byte %#x)", n, n ? p[0] : 0 );
        return 0;
    }
    *nal_len = (p[4] & 3) + 1;
    *count = 0;
    for (groups = 0; groups < 2; groups++)
    {
        uint32_t num;
        if (groups == 0) num = p[5] & 0x1f;
        else
        {
            if (pos >= n) break;
            num = p[pos++];
        }
        for (i = 0; i < num; i++)
        {
            uint32_t len;
            if (pos + 2 > n) goto bad;
            len = (p[pos] << 8) | p[pos + 1];
            pos += 2;
            if (!len || pos + len > n || *count >= MAV_MAX_PARAM_SETS) goto bad;
            sets[*count] = p + pos;
            sizes[*count] = len;
            ++*count;
            pos += len;
        }
    }
    if (*count < 2) goto bad;
    return 1;
bad:
    snprintf( why, why_size, "malformed avcC (%u bytes)", n );
    return 0;
}

/* hvcC: 22 header bytes (byte 21 low bits = len-1), numOfArrays, then
 * {u8 type, u16 count, {u16 len, NAL}...}...  Only VPS/SPS/PPS are kept. */
static int parse_hvcc( const uint8_t *p, uint32_t n, const uint8_t **sets, size_t *sizes, size_t *count,
                       int *nal_len, char *why, size_t why_size )
{
    uint32_t pos = 23, arrays, a, i;

    if (n < 23 || p[0] != 1)
    {
        snprintf( why, why_size, "HEVC codec data is not hvcC (%u bytes, first byte %#x)", n, n ? p[0] : 0 );
        return 0;
    }
    *nal_len = (p[21] & 3) + 1;
    arrays = p[22];
    *count = 0;
    for (a = 0; a < arrays; a++)
    {
        uint32_t type, num;
        if (pos + 3 > n) goto bad;
        type = p[pos] & 0x3f;
        num = (p[pos + 1] << 8) | p[pos + 2];
        pos += 3;
        for (i = 0; i < num; i++)
        {
            uint32_t len;
            if (pos + 2 > n) goto bad;
            len = (p[pos] << 8) | p[pos + 1];
            pos += 2;
            if (pos + len > n) goto bad;
            if (len && (type == 32 || type == 33 || type == 34))
            {
                if (*count >= MAV_MAX_PARAM_SETS) goto bad;
                sets[*count] = p + pos;
                sizes[*count] = len;
                ++*count;
            }
            pos += len;
        }
    }
    if (*count < 3) goto bad;
    return 1;
bad:
    snprintf( why, why_size, "malformed hvcC (%u bytes)", n );
    return 0;
}

static OSStatus vt_create_session( struct vt_dec *d )
{
    VTDecompressionOutputCallbackRecord cb = { vt_output, d };
    CFMutableDictionaryRef attrs;
    SInt32 pixfmt = kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange;
    CFNumberRef num;
    OSStatus status;

    attrs = CFDictionaryCreateMutable( kCFAllocatorDefault, 1, &kCFTypeDictionaryKeyCallBacks,
                                       &kCFTypeDictionaryValueCallBacks );
    if (!attrs) return -1;
    num = CFNumberCreate( kCFAllocatorDefault, kCFNumberSInt32Type, &pixfmt );
    CFDictionarySetValue( attrs, kCVPixelBufferPixelFormatTypeKey, num );
    CFRelease( num );
    status = VTDecompressionSessionCreate( kCFAllocatorDefault, d->fmt, NULL, attrs, &cb, &d->session );
    CFRelease( attrs );
    return status;
}

static int vt_supports( int codec )
{
    return codec == MAV_BACKEND_H264 || codec == MAV_BACKEND_HEVC;
}

static void vt_close( void *handle )
{
    struct vt_dec *d = handle;

    if (!d) return;
    if (d->session)
    {
        VTDecompressionSessionWaitForAsynchronousFrames( d->session );
        VTDecompressionSessionInvalidate( d->session );
        CFRelease( d->session );
    }
    if (d->fmt) CFRelease( d->fmt );
    free( d );
}

static void *vt_open( int codec, const uint8_t *extradata, uint32_t extradata_size,
                      uint32_t width, uint32_t height, char *why, size_t why_size )
{
    const uint8_t *sets[MAV_MAX_PARAM_SETS];
    size_t sizes[MAV_MAX_PARAM_SETS], count = 0;
    struct vt_dec *d;
    int nal_len = 4;
    OSStatus status;

    (void)width; (void)height;
    if (!vt_supports( codec ))
    {
        snprintf( why, why_size, "codec %d is not a VideoToolbox codec here", codec );
        return NULL;
    }
    if (!extradata || !extradata_size)
    {
        snprintf( why, why_size, "no codec data (avcC/hvcC) in the container" );
        return NULL;
    }
    if (codec == MAV_BACKEND_H264
        ? !parse_avcc( extradata, extradata_size, sets, sizes, &count, &nal_len, why, why_size )
        : !parse_hvcc( extradata, extradata_size, sets, sizes, &count, &nal_len, why, why_size ))
        return NULL;
    if (codec == MAV_BACKEND_HEVC && !VTIsHardwareDecodeSupported( kCMVideoCodecType_HEVC ))
    {
        snprintf( why, why_size, "this device has no HEVC decoder" );
        return NULL;
    }
    if (!(d = calloc( 1, sizeof(*d) )))
    {
        snprintf( why, why_size, "out of memory" );
        return NULL;
    }
    d->codec = codec;
    if (codec == MAV_BACKEND_H264)
        status = CMVideoFormatDescriptionCreateFromH264ParameterSets( kCFAllocatorDefault, count, sets, sizes,
                                                                      nal_len, &d->fmt );
    else
        status = CMVideoFormatDescriptionCreateFromHEVCParameterSets( kCFAllocatorDefault, count, sets, sizes,
                                                                      nal_len, NULL, &d->fmt );
    if (status)
    {
        snprintf( why, why_size, "CMVideoFormatDescriptionCreateFrom%sParameterSets failed (%d, %zu sets)",
                  codec == MAV_BACKEND_H264 ? "H264" : "HEVC", (int)status, count );
        vt_close( d );
        return NULL;
    }
    if ((status = vt_create_session( d )))
    {
        snprintf( why, why_size, "VTDecompressionSessionCreate failed (%d)", (int)status );
        vt_close( d );
        return NULL;
    }
    return d;
}

static int vt_decode( void *handle, const uint8_t *data, uint32_t size, int64_t pts, int64_t duration,
                      int keyframe, mav_vframe_emit emit, void *ctx )
{
    struct vt_dec *d = handle;
    CMBlockBufferRef block = NULL;
    CMSampleBufferRef sample = NULL;
    CMSampleTimingInfo timing;
    size_t sample_size = size;
    VTDecodeInfoFlags info = 0;
    OSStatus status;

    (void)keyframe;
    if (!size) return 0;
    if (!d->session && (status = vt_create_session( d ))) return status < 0 ? (int)status : -1;
    /* The packet memory outlives this call: decoding is synchronous. */
    status = CMBlockBufferCreateWithMemoryBlock( kCFAllocatorDefault, (void *)data, size, kCFAllocatorNull,
                                                 NULL, 0, size, 0, &block );
    if (status) return status < 0 ? (int)status : -1;
    timing.duration = duration != INT64_MIN ? CMTimeMake( duration, 1 ) : kCMTimeInvalid;
    timing.presentationTimeStamp = pts != INT64_MIN ? CMTimeMake( pts, 1 ) : kCMTimeInvalid;
    timing.decodeTimeStamp = kCMTimeInvalid;
    status = CMSampleBufferCreateReady( kCFAllocatorDefault, block, d->fmt, 1, 1, &timing, 1, &sample_size, &sample );
    CFRelease( block );
    if (status) return status < 0 ? (int)status : -1;

    d->emit = emit;
    d->ctx = ctx;
    d->frame_status = noErr;
    status = VTDecompressionSessionDecodeFrame( d->session, sample, 0, NULL, &info );
    if (status == noErr) VTDecompressionSessionWaitForAsynchronousFrames( d->session );
    d->emit = NULL;
    d->ctx = NULL;
    CFRelease( sample );

    if (status == kVTInvalidSessionErr)
    {
        /* iOS tears hardware sessions down when the app is backgrounded;
         * the next packet gets a fresh session (and recovers at the next
         * keyframe). */
        VTDecompressionSessionInvalidate( d->session );
        CFRelease( d->session );
        d->session = NULL;
    }
    if (status) return status < 0 ? (int)status : -1;
    if (d->frame_status) return d->frame_status < 0 ? (int)d->frame_status : -1;
    return 0;
}

static int vt_map( void *frame, struct mav_vplanes *planes )
{
    CVPixelBufferRef pb = frame;
    OSType fmt = CVPixelBufferGetPixelFormatType( pb );

    if (fmt != kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange
        && fmt != kCVPixelFormatType_420YpCbCr8BiPlanarFullRange)
        return -1;
    if (CVPixelBufferLockBaseAddress( pb, kCVPixelBufferLock_ReadOnly )) return -1;
    if (CVPixelBufferGetPlaneCount( pb ) < 2)
    {
        CVPixelBufferUnlockBaseAddress( pb, kCVPixelBufferLock_ReadOnly );
        return -1;
    }
    planes->y = CVPixelBufferGetBaseAddressOfPlane( pb, 0 );
    planes->uv = CVPixelBufferGetBaseAddressOfPlane( pb, 1 );
    planes->y_stride = (uint32_t)CVPixelBufferGetBytesPerRowOfPlane( pb, 0 );
    planes->uv_stride = (uint32_t)CVPixelBufferGetBytesPerRowOfPlane( pb, 1 );
    planes->width = (uint32_t)CVPixelBufferGetWidthOfPlane( pb, 0 );
    planes->height = (uint32_t)CVPixelBufferGetHeightOfPlane( pb, 0 );
    planes->full_range = fmt == kCVPixelFormatType_420YpCbCr8BiPlanarFullRange;
    if (!planes->y || !planes->uv)
    {
        CVPixelBufferUnlockBaseAddress( pb, kCVPixelBufferLock_ReadOnly );
        return -1;
    }
    return 0;
}

static void vt_unmap( void *frame )
{
    CVPixelBufferUnlockBaseAddress( (CVPixelBufferRef)frame, kCVPixelBufferLock_ReadOnly );
}

static void vt_release( void *frame )
{
    CVPixelBufferRelease( (CVPixelBufferRef)frame );
}

static void vt_flush( void *handle )
{
    struct vt_dec *d = handle;

    /* Drain whatever VideoToolbox still holds and drop it (no emit target),
     * then start the next packet with a fresh reference state. */
    if (d->session)
    {
        VTDecompressionSessionWaitForAsynchronousFrames( d->session );
        VTDecompressionSessionInvalidate( d->session );
        CFRelease( d->session );
        d->session = NULL;
    }
}

const struct mav_video_backend mav_apple_video_backend =
{
    "videotoolbox", vt_supports, vt_open, vt_decode, vt_map, vt_unmap, vt_release, vt_flush, vt_close,
};

/***********************************************************************
 *           AudioToolbox (AAC)
 */
#define MAV_AT_NO_MORE_DATA ((OSStatus)0x6d6e6474)   /* 'mndt', private to this file */

struct at_dec
{
    AudioConverterRef conv;
    AudioStreamBasicDescription in, out;
    const uint8_t *pkt;
    uint32_t pkt_size;
    int pending;
    AudioStreamPacketDescription desc;
};

/* An MPEG-4 ES_Descriptor wrapping the AudioSpecificConfig: the form
 * kAudioConverterDecompressionMagicCookie and kAudioFormatProperty_FormatInfo
 * take for AAC (the payload of an 'esds' box, ISO/IEC 14496-1 7.2.6.5). */
static void put_descr( uint8_t **p, int tag, uint32_t size )
{
    *(*p)++ = tag;
    *(*p)++ = 0x80 | ((size >> 21) & 0x7f);
    *(*p)++ = 0x80 | ((size >> 14) & 0x7f);
    *(*p)++ = 0x80 | ((size >> 7) & 0x7f);
    *(*p)++ = size & 0x7f;
}

static uint8_t *make_esds( const uint8_t *asc, uint32_t asc_size, uint32_t *size )
{
    uint32_t total = 5 + 3 + 5 + 13 + 5 + asc_size;
    uint8_t *cookie = malloc( total ), *p = cookie;

    if (!cookie) return NULL;
    put_descr( &p, 0x03, 3 + 5 + 13 + 5 + asc_size );   /* ES_Descriptor */
    *p++ = 0; *p++ = 0;                                  /* ES_ID */
    *p++ = 0;                                            /* flags */
    put_descr( &p, 0x04, 13 + 5 + asc_size );            /* DecoderConfigDescriptor */
    *p++ = 0x40;                                         /* objectTypeIndication: MPEG-4 audio */
    *p++ = 0x15;                                         /* streamType audio, upStream 0, reserved 1 */
    *p++ = 0; *p++ = 0; *p++ = 0;                        /* bufferSizeDB */
    memset( p, 0, 8 ); p += 8;                           /* maxBitrate, avgBitrate */
    put_descr( &p, 0x05, asc_size );                     /* DecoderSpecificInfo */
    memcpy( p, asc, asc_size );
    *size = total;
    return cookie;
}

static OSStatus at_input( AudioConverterRef conv, UInt32 *packets, AudioBufferList *data,
                          AudioStreamPacketDescription **desc, void *opaque )
{
    struct at_dec *d = opaque;

    (void)conv;
    if (!d->pending)
    {
        *packets = 0;
        return MAV_AT_NO_MORE_DATA;
    }
    data->mNumberBuffers = 1;
    data->mBuffers[0].mNumberChannels = d->in.mChannelsPerFrame;
    data->mBuffers[0].mDataByteSize = d->pkt_size;
    data->mBuffers[0].mData = (void *)d->pkt;
    *packets = 1;
    if (desc)
    {
        d->desc.mStartOffset = 0;
        d->desc.mVariableFramesInPacket = 0;
        d->desc.mDataByteSize = d->pkt_size;
        *desc = &d->desc;
    }
    d->pending = 0;
    return noErr;
}

static int at_supports( int codec )
{
    return codec == MAV_BACKEND_AAC;
}

static void at_close( void *handle )
{
    struct at_dec *d = handle;

    if (!d) return;
    if (d->conv) AudioConverterDispose( d->conv );
    free( d );
}

static void *at_open( int codec, const uint8_t *extradata, uint32_t extradata_size,
                      uint32_t *rate, uint32_t *channels, char *why, size_t why_size )
{
    struct at_dec *d;
    uint8_t *cookie;
    uint32_t cookie_size = 0;
    UInt32 size;
    OSStatus status;

    if (codec != MAV_BACKEND_AAC)
    {
        snprintf( why, why_size, "codec %d is not an AudioToolbox codec here", codec );
        return NULL;
    }
    if (!extradata || extradata_size < 2 || extradata_size > 64)
    {
        snprintf( why, why_size, "AAC without a usable AudioSpecificConfig (%u bytes)", extradata_size );
        return NULL;
    }
    if (!(d = calloc( 1, sizeof(*d) )) || !(cookie = make_esds( extradata, extradata_size, &cookie_size )))
    {
        free( d );
        snprintf( why, why_size, "out of memory" );
        return NULL;
    }

    d->in.mFormatID = kAudioFormatMPEG4AAC;
    d->in.mSampleRate = *rate;
    d->in.mChannelsPerFrame = *channels;
    size = sizeof(d->in);
    if (AudioFormatGetProperty( kAudioFormatProperty_FormatInfo, cookie_size, cookie, &size, &d->in ))
    {
        memset( &d->in, 0, sizeof(d->in) );
        d->in.mFormatID = kAudioFormatMPEG4AAC;
        d->in.mSampleRate = *rate;
        d->in.mChannelsPerFrame = *channels;
        d->in.mFramesPerPacket = 1024;
    }
    else
    {
        /* The first entry of the format list is the richest layer the
         * config describes (SBR / PS on top of AAC-LC). */
        AudioFormatInfo info = { d->in, cookie, cookie_size };
        UInt32 list_size = 0;
        if (!AudioFormatGetPropertyInfo( kAudioFormatProperty_FormatList, sizeof(info), &info, &list_size )
            && list_size >= sizeof(AudioFormatListItem))
        {
            AudioFormatListItem *items = malloc( list_size );
            if (items && !AudioFormatGetProperty( kAudioFormatProperty_FormatList, sizeof(info), &info,
                                                  &list_size, items ) && list_size >= sizeof(*items))
                d->in = items[0].mASBD;
            free( items );
        }
    }
    if (!d->in.mSampleRate || !d->in.mChannelsPerFrame || d->in.mChannelsPerFrame > 8)
    {
        snprintf( why, why_size, "AAC config gives rate %.0f channels %u", d->in.mSampleRate,
                  (unsigned)d->in.mChannelsPerFrame );
        goto fail;
    }

    d->out.mFormatID = kAudioFormatLinearPCM;
    d->out.mFormatFlags = kAudioFormatFlagIsFloat | kAudioFormatFlagIsPacked;
    d->out.mSampleRate = d->in.mSampleRate;
    d->out.mChannelsPerFrame = d->in.mChannelsPerFrame;
    d->out.mBitsPerChannel = 32;
    d->out.mBytesPerFrame = 4 * d->in.mChannelsPerFrame;
    d->out.mFramesPerPacket = 1;
    d->out.mBytesPerPacket = d->out.mBytesPerFrame;
    if ((status = AudioConverterNew( &d->in, &d->out, &d->conv )))
    {
        snprintf( why, why_size, "AudioConverterNew failed (%d, format %#x)", (int)status,
                  (unsigned)d->in.mFormatID );
        d->conv = NULL;
        goto fail;
    }
    if ((status = AudioConverterSetProperty( d->conv, kAudioConverterDecompressionMagicCookie, cookie_size, cookie )))
    {
        snprintf( why, why_size, "the AAC decoder refused the codec config (%d)", (int)status );
        goto fail;
    }
    if (d->in.mChannelsPerFrame > 2)
    {
        /* AAC's own channel order is C L R ...; WAVE order is L R C LFE ... */
        AudioChannelLayout layout;
        memset( &layout, 0, sizeof(layout) );
        if (d->in.mChannelsPerFrame == 6) layout.mChannelLayoutTag = kAudioChannelLayoutTag_MPEG_5_1_A;
        else if (d->in.mChannelsPerFrame == 8) layout.mChannelLayoutTag = kAudioChannelLayoutTag_MPEG_7_1_C;
        else
        {
            snprintf( why, why_size, "%u-channel AAC has no WAVE channel order here",
                      (unsigned)d->in.mChannelsPerFrame );
            goto fail;
        }
        if ((status = AudioConverterSetProperty( d->conv, kAudioConverterOutputChannelLayout,
                                                 sizeof(layout), &layout )))
        {
            snprintf( why, why_size, "cannot set the %u-channel output order (%d)",
                      (unsigned)d->in.mChannelsPerFrame, (int)status );
            goto fail;
        }
    }
    free( cookie );
    *rate = (uint32_t)d->out.mSampleRate;
    *channels = d->out.mChannelsPerFrame;
    return d;

fail:
    free( cookie );
    at_close( d );
    return NULL;
}

static int at_decode( void *handle, const uint8_t *data, uint32_t size, float *out, uint32_t max_frames )
{
    struct at_dec *d = handle;
    AudioBufferList list;
    UInt32 frames = max_frames;
    OSStatus status;

    if (!size) return 0;
    d->pkt = data;
    d->pkt_size = size;
    d->pending = 1;
    list.mNumberBuffers = 1;
    list.mBuffers[0].mNumberChannels = d->out.mChannelsPerFrame;
    list.mBuffers[0].mDataByteSize = max_frames * d->out.mBytesPerFrame;
    list.mBuffers[0].mData = out;
    status = AudioConverterFillComplexBuffer( d->conv, at_input, d, &frames, &list, NULL );
    d->pending = 0;
    if (status && status != MAV_AT_NO_MORE_DATA && !frames)
        return status < 0 ? (int)status : -(int)(status & 0x7fffffff);
    return (int)frames;
}

static void at_flush( void *handle )
{
    struct at_dec *d = handle;
    AudioConverterReset( d->conv );
}

const struct mav_audio_backend mav_apple_audio_backend =
{
    "audiotoolbox", at_supports, at_open, at_decode, at_flush, at_close,
};

#endif /* __APPLE__ */
