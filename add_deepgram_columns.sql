-- Add new columns to transcription_results table for Deepgram extra fields
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS detected_language VARCHAR(10);
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS sentiment_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS topics_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS intents_data JSON;
ALTER TABLE transcription_results ADD COLUMN IF NOT EXISTS raw_response JSON;