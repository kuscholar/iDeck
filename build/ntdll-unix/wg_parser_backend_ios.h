/* The decoder backends of the wg_parser core (wg_parser_av_ios.c).
 *                                                        (MADEIRA ml1990)
 *
 * FFmpeg in this port is built WITHOUT H.264, HEVC and AAC decoders
 * (build/ffmpeg/build.sh); those streams are decoded by the platform
 * instead -- VideoToolbox and AudioToolbox, in wg_parser_apple_ios.c.  This
 * header is the whole contract between the core and such a backend, and it
 * deliberately uses no Wine, FFmpeg or Apple type, so that:
 *
 *   - the Apple backend is its own translation unit and never sees Wine's
 *     headers (CoreFoundation and winnt.h disagree about several names);
 *   - tests/host/check-wg-parser.py can drive the core's demux, packet
 *     queue, reorder, seek and pixel-conversion logic on Linux through a stub
 *     backend of the same shape.
 *
 * Threading: every call is made with the parser's lock held, one at a time.
 * The video `decode` hands finished pictures back through `emit` before it
 * returns (possibly from another thread while the caller waits), in DECODE
 * order; the core re-orders them by presentation time.
 */
#ifndef MADEIRA_WG_PARSER_BACKEND_IOS_H
#define MADEIRA_WG_PARSER_BACKEND_IOS_H

#include <stddef.h>
#include <stdint.h>

enum mav_backend_codec
{
    MAV_BACKEND_H264 = 1,       /* extradata: avcC (ISO/IEC 14496-15), length-prefixed NAL packets */
    MAV_BACKEND_HEVC = 2,       /* extradata: hvcC, length-prefixed NAL packets */
    MAV_BACKEND_AAC = 16,       /* extradata: AudioSpecificConfig, one raw access unit per packet */
};

/* One decoded picture, 4:2:0 bi-planar (NV12 layout: Y plane, then an
 * interleaved CbCr plane at half height).  Valid between map and unmap. */
struct mav_vplanes
{
    const uint8_t *y, *uv;
    uint32_t y_stride, uv_stride;
    uint32_t width, height;     /* of the picture actually decoded */
    int full_range;             /* 0: video range (16-235), 1: full range */
};

/* `pts` / `duration` are the values passed to decode() for the packet the
 * picture came from, in the stream's own time base (INT64_MIN: unknown). */
typedef void (*mav_vframe_emit)( void *ctx, void *frame, int64_t pts, int64_t duration );

struct mav_video_backend
{
    const char *name;
    int (*supports)( int codec );
    void *(*open)( int codec, const uint8_t *extradata, uint32_t extradata_size,
                   uint32_t width, uint32_t height, char *why, size_t why_size );
    /* < 0 on a decoding error (the packet is lost, the stream goes on) */
    int (*decode)( void *dec, const uint8_t *data, uint32_t size, int64_t pts, int64_t duration,
                   int keyframe, mav_vframe_emit emit, void *ctx );
    int (*map)( void *frame, struct mav_vplanes *planes );
    void (*unmap)( void *frame );
    void (*release)( void *frame );
    /* after a seek: forget reference pictures; nothing is emitted */
    void (*flush)( void *dec );
    void (*close)( void *dec );
};

struct mav_audio_backend
{
    const char *name;
    int (*supports)( int codec );
    /* *rate / *channels: in, what the container says; out, what decode()
     * produces (an SBR stream may double the rate). */
    void *(*open)( int codec, const uint8_t *extradata, uint32_t extradata_size,
                   uint32_t *rate, uint32_t *channels, char *why, size_t why_size );
    /* One packet in, interleaved float32 out.  Returns the frames written
     * (0 is legal: the decoder may hold the first packet back), < 0 on a
     * decoding error. */
    int (*decode)( void *dec, const uint8_t *data, uint32_t size, float *out, uint32_t max_frames );
    void (*flush)( void *dec );
    void (*close)( void *dec );
};

/* Largest output of one audio decode() call, in frames. */
#define MAV_AUDIO_BACKEND_MAX_FRAMES 8192

#ifdef __APPLE__
extern const struct mav_video_backend mav_apple_video_backend;
extern const struct mav_audio_backend mav_apple_audio_backend;
#endif

#endif /* MADEIRA_WG_PARSER_BACKEND_IOS_H */
