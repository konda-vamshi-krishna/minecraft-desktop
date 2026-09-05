/**
 * @file audio.h
 * @brief Real-Time Procedural 8-Bit Sound Synthesizer & 16-Voice Polyphonic Mixer.
 *
 * Implements mathematical sound synthesis (zero external audio files):
 * - SFX_CLICK: UI Click (15ms, 2400 Hz square wave, linear decay)
 * - SFX_STEP: Footstep (40ms, 16-bit Galois LFSR noise + 80 Hz triangle thump, exp decay lambda=65)
 * - SFX_JUMP: Jump (90ms, 25% duty square wave, 140 -> 560 Hz ascending sweep, 5ms attack, 85ms decay)
 * - SFX_BLOCK_BREAK: Block Break (160ms, modulated LFSR noise + falling square subharmonic 120 -> 0 Hz, power decay)
 * - SFX_BLOCK_PLACE: Block Place (50ms, triangle wave pitch plummet 220*2^(-25t), exp decay e^(-50t))
 *
 * Mixer features:
 * - 16-voice polyphonic real-time mixer
 * - Ring voice stealing when all voices saturated
 * - Hard saturation limiter [-1.0, 1.0]
 * - Zero dynamic heap allocations
 *
 * ponytail: [procedural real-time math evaluation] -> [precomputed static PCM wave lookup tables]
 * ponytail: [pure synthetic square/noise] -> [2-pole resonant biquad filter + Freeverb procedural DSP]
 */

#ifndef MINECRAFT_AUDIO_AUDIO_H
#define MINECRAFT_AUDIO_AUDIO_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MAX_ACTIVE_VOICES 16
#define SAMPLE_RATE       44100

/* ============================================================================
 * Sound Event Identifiers (docs/04 §6.3)
 * ============================================================================ */
typedef enum SoundID {
    SFX_NONE = 0,
    SFX_CLICK,
    SFX_STEP,
    SFX_JUMP,
    SFX_BLOCK_BREAK,
    SFX_BLOCK_PLACE,
    SFX_COUNT
} SoundID;

/* SoundEvent compatibility enum matching PROJECT.md §Interface Contracts */
typedef enum SoundEvent {
    SOUND_CLICK = SFX_CLICK,
    SOUND_STEP  = SFX_STEP,
    SOUND_JUMP  = SFX_JUMP,
    SOUND_BREAK = SFX_BLOCK_BREAK,
    SOUND_PLACE = SFX_BLOCK_PLACE,
    SOUND_COUNT = SFX_COUNT
} SoundEvent;

/* Active synthesizer voice state */
typedef struct Voice {
    SoundID id;
    int cursor;         /* Current sample index within sound duration */
    int totalSamples;   /* Total duration in samples */
    float phase;        /* Oscillator phase [0.0, 1.0) */
    uint16_t lfsr;      /* Voice-local noise state */
    float volume;       /* Linear volume scalar [0.0, 1.0] */
} Voice;

/* 16-voice software audio mixer */
typedef struct AudioMixer {
    Voice voices[MAX_ACTIVE_VOICES];
    int sampleRate;
    int nextStealIndex;
    bool isInitialized;
} AudioMixer;

/* ============================================================================
 * Mixer API Functions
 * ============================================================================ */

/**
 * @brief Initializes the audio mixer subsystem.
 * @param sampleRate Output PCM sample rate in Hz (e.g. 44100).
 */
void Audio_Init(int sampleRate);

/**
 * @brief Triggers playback of a procedural sound effect.
 * @param id Sound identifier (SFX_CLICK, SFX_STEP, etc.).
 * @param volume Linear volume scale [0.0, 1.0]. Volumes <= 0.001 are culled.
 */
void Audio_PlaySound(SoundID id, float volume);

/**
 * @brief PROJECT.md compatibility interface: triggers sound with volume and pitch.
 */
void Audio_PlaySoundEvent(SoundEvent event, float volume, float pitch);

/**
 * @brief Main audio streaming callback called synchronously by audio driver.
 *        Renders frameCount mixed float samples into outputBuffer with hard [-1.0, 1.0] limiter.
 * @param outputBuffer Pointer to float PCM buffer.
 * @param frameCount Number of samples (frames) to render.
 */
void AudioMixerCallback(float* outputBuffer, int frameCount);

/**
 * @brief PROJECT.md compatibility interface alias for AudioMixerCallback.
 */
void Audio_MixCallback(float* outputBuffer, int frameCount);

/**
 * @brief Shuts down the mixer and releases all active voices.
 */
void Audio_Shutdown(void);

/**
 * @brief Returns the count of currently playing/active voices.
 */
int Audio_GetActiveVoiceCount(void);

/**
 * @brief Synthesizes an entire sound into a pre-allocated buffer for offline analysis or testing.
 * @param id Sound identifier.
 * @param buffer Output float buffer of at least maxSamples capacity.
 * @param maxSamples Buffer capacity.
 * @return Number of samples written.
 */
int Audio_SynthesizeSound(SoundID id, float* buffer, int maxSamples);

/**
 * @brief Inspects voice state at specified voice channel index [0..MAX_ACTIVE_VOICES-1].
 */
const Voice* Audio_GetVoice(int index);

#ifdef __cplusplus
}
#endif

#endif /* MINECRAFT_AUDIO_AUDIO_H */
