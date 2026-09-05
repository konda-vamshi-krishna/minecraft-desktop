/**
 * @file synthesizer.c
 * @brief Real-Time Procedural 8-Bit Audio Synthesizer & 16-Voice Software Mixer.
 *
 * ponytail: [procedural real-time math evaluation] -> [precomputed static PCM wave lookup tables]
 * ponytail: [pure synthetic square/noise] -> [2-pole resonant biquad filter + Freeverb procedural DSP]
 */

#include "audio.h"
#include <math.h>
#include <string.h>

/* Global static software mixer state (zero dynamic heap allocation) */
static AudioMixer g_Mixer = {
    .sampleRate = SAMPLE_RATE,
    .nextStealIndex = 0,
    .isInitialized = false
};

/* ============================================================================
 * Internal Mathematical Waveform Synthesizer Helper
 * ============================================================================ */

static inline float SynthesizeVoiceSample(Voice* v, int sampleRate) {
    float t = (float)v->cursor / (float)sampleRate;
    float sample = 0.0f;

    switch (v->id) {
        case SFX_CLICK: {
            /* 15ms duration, 2400 Hz square wave, 50% duty cycle, linear decay */
            float freq = 2400.0f;
            float phase = fmodf(freq * t, 1.0f);
            float sq = (phase < 0.5f) ? 1.0f : -1.0f;
            float env = 1.0f - ((float)v->cursor / (float)v->totalSamples);
            if (env < 0.0f) env = 0.0f;
            sample = sq * env;
            break;
        }

        case SFX_STEP: {
            /* 40ms duration, 16-bit Galois LFSR noise + 80 Hz triangle thump, exp decay lambda=65 */
            uint16_t bit = ((v->lfsr >> 0) ^ (v->lfsr >> 2) ^ (v->lfsr >> 3) ^ (v->lfsr >> 5)) & 1u;
            v->lfsr = (v->lfsr >> 1) | (bit << 15);
            float noise = ((float)v->lfsr / 32767.5f) - 1.0f;

            float thump_phase = fmodf(80.0f * t, 1.0f);
            float thump = 4.0f * fabsf(thump_phase - 0.5f) - 1.0f;

            float env = expf(-65.0f * t);
            sample = (0.7f * noise + 0.3f * thump) * env;
            break;
        }

        case SFX_JUMP: {
            /* 90ms duration, 25% duty square sweep 140 -> 560 Hz, linear attack/decay */
            float duration = (float)v->totalSamples / (float)sampleRate;
            float f_t = 140.0f + (420.0f * (t / duration));
            v->phase = fmodf(v->phase + f_t / (float)sampleRate, 1.0f);
            float sq = (v->phase < 0.25f) ? 1.0f : -1.0f;

            float env;
            if (t < 0.005f) {
                env = t / 0.005f; /* 5ms linear attack */
            } else {
                env = 1.0f - ((t - 0.005f) / 0.085f); /* 85ms linear decay */
                if (env < 0.0f) env = 0.0f;
            }
            sample = sq * env;
            break;
        }

        case SFX_BLOCK_BREAK: {
            /* 160ms duration, modulated LFSR noise + pitch-falling square subharmonic 120 -> 0 Hz */
            uint16_t bit = ((v->lfsr >> 0) ^ (v->lfsr >> 2) ^ (v->lfsr >> 3) ^ (v->lfsr >> 5)) & 1u;
            v->lfsr = (v->lfsr >> 1) | (bit << 15);
            float noise = ((float)v->lfsr / 32767.5f) - 1.0f;

            float duration = (float)v->totalSamples / (float)sampleRate;
            float f_sub = 120.0f * (1.0f - t / duration);
            v->phase = fmodf(v->phase + f_sub / (float)sampleRate, 1.0f);
            float sq = (v->phase < 0.5f) ? 1.0f : -1.0f;

            float norm_t = t / duration;
            float env = 1.0f - powf(norm_t, 0.7f);
            if (env < 0.0f) env = 0.0f;

            sample = (0.85f * noise + 0.15f * sq) * env;
            break;
        }

        case SFX_BLOCK_PLACE: {
            /* 50ms duration, triangle wave pitch plummet 220*2^(-25t), exp decay e^(-50t) */
            float f_t = 220.0f * powf(2.0f, -25.0f * t);
            v->phase = fmodf(v->phase + f_t / (float)sampleRate, 1.0f);
            float tri = 4.0f * fabsf(v->phase - 0.5f) - 1.0f;
            float env = expf(-50.0f * t);
            sample = tri * env;
            break;
        }

        default:
            sample = 0.0f;
            break;
    }

    return sample;
}

/* ============================================================================
 * Mixer API Implementation
 * ============================================================================ */

void Audio_Init(int sampleRate) {
    g_Mixer.sampleRate = (sampleRate > 0) ? sampleRate : SAMPLE_RATE;
    g_Mixer.nextStealIndex = 0;
    g_Mixer.isInitialized = true;

    for (int i = 0; i < MAX_ACTIVE_VOICES; i++) {
        g_Mixer.voices[i].id = SFX_NONE;
        g_Mixer.voices[i].cursor = 0;
        g_Mixer.voices[i].totalSamples = 0;
        g_Mixer.voices[i].phase = 0.0f;
        g_Mixer.voices[i].lfsr = 0;
        g_Mixer.voices[i].volume = 0.0f;
    }
}

void Audio_Shutdown(void) {
    for (int i = 0; i < MAX_ACTIVE_VOICES; i++) {
        g_Mixer.voices[i].id = SFX_NONE;
    }
    g_Mixer.isInitialized = false;
}

void Audio_PlaySound(SoundID id, float volume) {
    if (!g_Mixer.isInitialized) {
        Audio_Init(SAMPLE_RATE);
    }

    /* Ponytail Rung 1: Negligible volume skips voice allocation */
    if (volume <= 0.001f || id <= SFX_NONE || id >= SFX_COUNT) {
        return;
    }

    float clampedVol = (volume > 1.0f) ? 1.0f : volume;

    /* Find idle voice channel */
    int target = -1;
    for (int i = 0; i < MAX_ACTIVE_VOICES; i++) {
        if (g_Mixer.voices[i].id == SFX_NONE) {
            target = i;
            break;
        }
    }

    /* If all 16 voices are saturated, steal via ring allocator */
    if (target == -1) {
        target = g_Mixer.nextStealIndex;
        g_Mixer.nextStealIndex = (g_Mixer.nextStealIndex + 1) % MAX_ACTIVE_VOICES;
    }

    Voice* v = &g_Mixer.voices[target];
    v->id = id;
    v->cursor = 0;
    v->phase = 0.0f;
    v->volume = clampedVol;

    int sr = g_Mixer.sampleRate;
    switch (id) {
        case SFX_CLICK:
            v->totalSamples = (int)(0.015f * sr);
            v->lfsr = 0;
            break;
        case SFX_STEP:
            v->totalSamples = (int)(0.040f * sr);
            v->lfsr = 0xACE1u;
            break;
        case SFX_JUMP:
            v->totalSamples = (int)(0.090f * sr);
            v->lfsr = 0;
            break;
        case SFX_BLOCK_BREAK:
            v->totalSamples = (int)(0.160f * sr);
            v->lfsr = 0x1337u;
            break;
        case SFX_BLOCK_PLACE:
            v->totalSamples = (int)(0.050f * sr);
            v->lfsr = 0;
            break;
        default:
            v->totalSamples = 0;
            v->id = SFX_NONE;
            break;
    }
}

void Audio_PlaySoundEvent(SoundEvent event, float volume, float pitch) {
    (void)pitch; /* ponytail: pitch modulation reserved for future DSP upgrade */
    Audio_PlaySound((SoundID)event, volume);
}

void AudioMixerCallback(float* outputBuffer, int frameCount) {
    if (!outputBuffer || frameCount <= 0) return;

    for (int f = 0; f < frameCount; f++) {
        float mix = 0.0f;

        for (int i = 0; i < MAX_ACTIVE_VOICES; i++) {
            Voice* v = &g_Mixer.voices[i];
            if (v->id == SFX_NONE) continue;

            float sample = SynthesizeVoiceSample(v, g_Mixer.sampleRate);
            mix += sample * v->volume;

            v->cursor++;
            if (v->cursor >= v->totalSamples) {
                v->id = SFX_NONE; /* Release voice */
            }
        }

        /* Hard saturation limiter [-1.0, 1.0] */
        if (mix > 1.0f) mix = 1.0f;
        else if (mix < -1.0f) mix = -1.0f;

        outputBuffer[f] = mix;
    }
}

void Audio_MixCallback(float* outputBuffer, int frameCount) {
    AudioMixerCallback(outputBuffer, frameCount);
}

int Audio_GetActiveVoiceCount(void) {
    int count = 0;
    for (int i = 0; i < MAX_ACTIVE_VOICES; i++) {
        if (g_Mixer.voices[i].id != SFX_NONE) {
            count++;
        }
    }
    return count;
}

int Audio_SynthesizeSound(SoundID id, float* buffer, int maxSamples) {
    if (!buffer || maxSamples <= 0 || id <= SFX_NONE || id >= SFX_COUNT) {
        return 0;
    }

    Voice v;
    memset(&v, 0, sizeof(Voice));
    v.id = id;
    v.cursor = 0;
    v.phase = 0.0f;
    v.volume = 1.0f;

    int sr = (g_Mixer.sampleRate > 0) ? g_Mixer.sampleRate : SAMPLE_RATE;
    switch (id) {
        case SFX_CLICK:       v.totalSamples = (int)(0.015f * sr); v.lfsr = 0; break;
        case SFX_STEP:        v.totalSamples = (int)(0.040f * sr); v.lfsr = 0xACE1u; break;
        case SFX_JUMP:        v.totalSamples = (int)(0.090f * sr); v.lfsr = 0; break;
        case SFX_BLOCK_BREAK: v.totalSamples = (int)(0.160f * sr); v.lfsr = 0x1337u; break;
        case SFX_BLOCK_PLACE: v.totalSamples = (int)(0.050f * sr); v.lfsr = 0; break;
        default: return 0;
    }

    int samplesToWrite = (v.totalSamples < maxSamples) ? v.totalSamples : maxSamples;
    for (int i = 0; i < samplesToWrite; i++) {
        buffer[i] = SynthesizeVoiceSample(&v, sr);
        v.cursor++;
    }

    return samplesToWrite;
}

const Voice* Audio_GetVoice(int index) {
    if (index < 0 || index >= MAX_ACTIVE_VOICES) return NULL;
    return &g_Mixer.voices[index];
}
