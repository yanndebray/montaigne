#!/bin/bash

# Exit on error
set -e

echo "=== Starting Montaigne ElevenLabs Integration Test ==="

# 1. Test Voice Listing
echo -e "\n[Test 1] Testing Voice Listing..."
essai audio --provider elevenlabs --list-voices

# 2. Test Audio Generation (Provider: ElevenLabs, Voice: Adam)
# We use a dummy script or an existing one if available
echo -e "\n[Test 2] Testing ElevenLabs Audio Generation (Adam)..."
# Create a tiny dummy script for testing
cat <<EOF > test_voiceover.md
## SLIDE 1: Test
**[Duration: 5s]**
This is a test of the ElevenLabs integration using the Adam voice.
EOF

essai audio --script test_voiceover.md --provider elevenlabs --voice adam

# 3. Check for WAV output (Acceptance Criteria requirement)
echo -e "\n[Test 3] Verifying file format (Should be WAV)..."
if ls test_voiceover_audio/slide_01.wav >/dev/null 2>&1; then
    echo "SUCCESS: Found WAV file for ElevenLabs output."
else
    echo "FAILURE: WAV file not found. Check ffmpeg conversion in elevenlabs_tts.py."
    exit 1
fi

# 4. Test Default Voice Logic (George)
echo -e "\n[Test 4] Testing ElevenLabs Default Voice (George)..."
essai audio --script test_voiceover.md --provider elevenlabs
echo "SUCCESS: Default provider logic executed."

# 5. Test Full Video Pipeline with ElevenLabs
# Note: Requires a test.pdf in the directory
if [ -f "test.pdf" ]; then
    echo -e "\n[Test 5] Testing Full Video Pipeline with ElevenLabs..."
    essai video --pdf test.pdf --provider elevenlabs --voice bob
    echo "SUCCESS: Full video pipeline completed."
else
    echo -e "\n[Skip] Skipping Test 5 (No test.pdf found in root)."
fi

echo -e "\n=== All Tests Passed Successfully! ==="