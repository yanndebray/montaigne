# Montaigne - ElevenLabs Integration

Montaigne now supports ElevenLabs as a high-quality alternative to Gemini for text-to-speech (TTS) generation. This allows you to generate professional-grade voiceovers for your presentations.

## Setup

### 1. API Key

You must have an ElevenLabs API key. Add it to your `.env` file:

```bash
GEMINI_API_KEY=your-gemini-key
ELEVENLABS_API_KEY=your-elevenlabs-key-here
```

### 2. Dependencies

Ensure you have the ElevenLabs SDK installed. You can run the setup command:

```bash
essai setup
```

## Usage

### List Available Voices

Before generating audio, you can see which ElevenLabs voices are configured in the system:

```bash
essai audio --provider elevenlabs --list-voices
```

### Generate Audio

To use ElevenLabs for your voiceover script, specify the `--provider` flag:

```bash
# Generate using the default voice (George)
essai audio --script voiceover.md --provider elevenlabs

# Generate using a specific voice
essai audio --script voiceover.md --provider elevenlabs --voice adam
```

### Video Generation (Full Pipeline)

You can trigger ElevenLabs directly during the full PDF-to-Video pipeline:

```bash
essai video --pdf presentation.pdf --provider elevenlabs --voice bob
```