import React, { useState, useEffect, useRef } from 'react';
import { Mic, Download, Loader2 } from 'lucide-react';
import { toolsApi, preferencesApi } from '../services/api';

const MODEL_POLL_MS = 800;

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'pl', label: 'Polish' },
  { value: 'tr', label: 'Turkish' },
  { value: 'ru', label: 'Russian' },
  { value: 'nl', label: 'Dutch' },
  { value: 'cs', label: 'Czech' },
  { value: 'ar', label: 'Arabic' },
  { value: 'zh-cn', label: 'Chinese (Simplified)' },
  { value: 'ja', label: 'Japanese' },
  { value: 'hu', label: 'Hungarian' },
  { value: 'ko', label: 'Korean' },
];

interface VoiceCloningPanelProps {
  onTracksUpdated?: () => void | Promise<void>;
}

export const VoiceCloningPanel: React.FC<VoiceCloningPanelProps> = ({ onTracksUpdated }) => {
  const [text, setText] = useState('');
  const [speakerFile, setSpeakerFile] = useState<File | null>(null);
  const [outputFilename, setOutputFilename] = useState('voice_clone_output');
  const [language, setLanguage] = useState('en');
  const [device, setDevice] = useState('auto');
  const [temperature, setTemperature] = useState(0.75);
  const [lengthPenalty, setLengthPenalty] = useState(1.0);
  const [repetitionPenalty, setRepetitionPenalty] = useState(5.0);
  const [topK, setTopK] = useState(50);
  const [topP, setTopP] = useState(0.85);
  const [speed, setSpeed] = useState(1.0);
  const [enableTextSplitting, setEnableTextSplitting] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [modelReady, setModelReady] = useState<boolean | null>(null);
  const [modelState, setModelState] = useState('');
  const [modelMessage, setModelMessage] = useState('');
  const [modelDownloadProgress, setModelDownloadProgress] = useState<number | null>(null);
  const modelPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    toolsApi.voiceCloneModelStatus()
      .then((r) => {
        setModelReady(r.ready);
        setModelState(r.state || '');
        setModelMessage(r.message || '');
      })
      .catch(() => setModelReady(false));
  }, []);

  useEffect(() => {
    if (modelState !== 'downloading') {
      setModelDownloadProgress(null);
      if (modelPollRef.current) {
        clearInterval(modelPollRef.current);
        modelPollRef.current = null;
      }
      return;
    }
    const poll = () => {
      toolsApi.voiceCloneModelStatus()
        .then((r) => {
          setModelReady(r.ready);
          setModelState(r.state || '');
          setModelMessage(r.message || '');
        })
        .catch(() => {});
      toolsApi.getProgress()
        .then((p) => {
          if (p.stage === 'voice_clone_model_download') {
            setModelDownloadProgress(p.fraction);
          }
        })
        .catch(() => {});
    };
    poll();
    modelPollRef.current = setInterval(poll, MODEL_POLL_MS);
    return () => {
      if (modelPollRef.current) clearInterval(modelPollRef.current);
    };
  }, [modelState]);

  useEffect(() => {
    preferencesApi.get()
      .then((prefs) => {
        const v = prefs.voice_clone as Record<string, unknown> | undefined;
        if (v?.language != null) setLanguage(String(v.language));
        if (v?.device_preference != null) setDevice(String(v.device_preference));
        if (v?.output_filename != null) setOutputFilename(String(v.output_filename));
      })
      .catch(() => {});
  }, []);

  const handleDownloadModels = () => {
    setError(null);
    toolsApi.voiceCloneModelEnsure().then(() => {
      setModelState('downloading');
      setModelMessage('Downloading XTTS voice cloning model (first use only). This may take several minutes.');
    }).catch((e) => setError(e.message));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (modelReady !== true || modelState === 'downloading') {
      setError(modelState === 'downloading'
        ? 'Please wait for the voice cloning model download to finish.'
        : 'Voice cloning model is not ready. Click "Download voice cloning model" first.');
      return;
    }
    if (!(text || '').trim()) {
      setError('Text to synthesize is required.');
      return;
    }
    if (!speakerFile) {
      setError('Reference audio file is required.');
      return;
    }
    const out = (outputFilename || 'voice_clone_output').trim();
    if (!out) {
      setError('Output filename is required.');
      return;
    }
    const formData = new FormData();
    formData.set('text', text.trim());
    formData.append('speaker_wav', speakerFile);
    formData.set('output_filename', out.endsWith('.mp3') || out.endsWith('.wav') ? out : `${out}.mp3`);
    formData.set('language', language);
    formData.set('device_preference', device);
    formData.set('temperature', String(temperature));
    formData.set('length_penalty', String(lengthPenalty));
    formData.set('repetition_penalty', String(repetitionPenalty));
    formData.set('top_k', String(topK));
    formData.set('top_p', String(topP));
    formData.set('speed', String(speed));
    formData.set('enable_text_splitting', enableTextSplitting ? 'true' : 'false');
    setLoading(true);
    try {
      const prefs = await preferencesApi.get();
      if (prefs.output_dir) formData.set('out_dir', prefs.output_dir);
      const res = await toolsApi.voiceClone(formData);
      if (res?.error) {
        setError(res.message || 'Voice cloning failed.');
        setLoading(false);
        return;
      }
      await preferencesApi.update({
        voice_clone: {
          language,
          device_preference: device,
          output_filename: out.endsWith('.mp3') || out.endsWith('.wav') ? out : `${out}.mp3`,
        },
      });
      setSuccess(res?.message || 'Voice cloning completed!');
      onTracksUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Voice cloning failed.');
    }
    setLoading(false);
  };

  return (
    <div className="h-full flex flex-col overflow-y-auto p-4 text-zinc-800 dark:text-zinc-200">
      <div className="flex items-center gap-2 mb-4">
        <Mic className="w-6 h-6 text-pink-500" />
        <h2 className="text-lg font-semibold">Voice Cloning</h2>
      </div>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
        Clone a voice from a reference audio file using XTTS v2. Upload a reference and enter text to synthesize.
      </p>

      {modelReady === false && modelState !== 'downloading' && (
        <div className="mb-4 p-3 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-400 text-sm">
          <p className="font-medium mb-1">Voice cloning model is not downloaded yet.</p>
          <p className="mb-2">{modelMessage || 'Click "Download voice cloning model" to download it (first use only).'}</p>
          <button
            type="button"
            onClick={handleDownloadModels}
            className="inline-flex items-center gap-1 rounded-lg bg-amber-500 text-white px-3 py-1.5 text-sm font-medium hover:bg-amber-600"
          >
            <Download size={14} /> Download voice cloning model
          </button>
        </div>
      )}
      {modelState === 'downloading' && (
        <div className="mb-4 p-3 rounded-lg bg-blue-500/10 text-blue-700 dark:text-blue-400 text-sm">
          <p className="font-medium mb-2 flex items-center gap-2">
            <Loader2 size={16} className="animate-spin" /> Downloading XTTS voice cloning model…
          </p>
          <div className="w-full h-2 rounded-full bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
            <div
              className="h-full bg-pink-500 transition-all duration-300"
              style={{ width: modelDownloadProgress != null ? `${modelDownloadProgress * 100}%` : '30%' }}
            />
          </div>
        </div>
      )}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 text-red-600 dark:text-red-400 text-sm">{error}</div>
      )}
      {success && (
        <div className="mb-4 p-3 rounded-lg bg-green-500/10 text-green-700 dark:text-green-400 text-sm">{success}</div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label className="block text-sm font-medium mb-1">Text to Synthesize</label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="Enter the text you want to synthesize in the cloned voice..."
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Reference Audio File</label>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.flac"
            onChange={(e) => setSpeakerFile(e.target.files?.[0] || null)}
            className="w-full text-sm file:mr-2 file:rounded-lg file:border-0 file:bg-pink-500 file:px-3 file:py-2 file:text-white file:text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Output filename</label>
          <input
            type="text"
            value={outputFilename}
            onChange={(e) => setOutputFilename(e.target.value)}
            placeholder="voice_clone_output"
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          >
            {LANGUAGES.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Device</label>
          <select
            value={device}
            onChange={(e) => setDevice(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          >
            <option value="auto">Auto (MPS if available, else CPU)</option>
            <option value="mps">Apple Silicon GPU (MPS)</option>
            <option value="cpu">CPU</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Temperature: {temperature}</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Length Penalty: {lengthPenalty}</label>
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={lengthPenalty}
            onChange={(e) => setLengthPenalty(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Repetition Penalty: {repetitionPenalty}</label>
          <input
            type="range"
            min={0}
            max={10}
            step={0.1}
            value={repetitionPenalty}
            onChange={(e) => setRepetitionPenalty(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Top-K</label>
          <input
            type="number"
            min={1}
            max={100}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Top-P: {topP}</label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={topP}
            onChange={(e) => setTopP(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Speed: {speed}</label>
          <input
            type="range"
            min={0.25}
            max={4}
            step={0.05}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
            className="w-full"
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enableTextSplitting}
            onChange={(e) => setEnableTextSplitting(e.target.checked)}
          />
          <span className="text-sm">Enable Text Splitting</span>
        </label>

        <button
          type="submit"
          disabled={loading || modelReady !== true || modelState === 'downloading'}
          className="rounded-lg bg-pink-500 text-white px-4 py-2 text-sm font-medium hover:bg-pink-600 disabled:opacity-50"
        >
          {modelState === 'downloading' ? (
            <><Loader2 size={16} className="animate-spin inline mr-1" /> Downloading model…</>
          ) : loading ? (
            'Cloning…'
          ) : (
            'Clone Voice'
          )}
        </button>
      </form>
    </div>
  );
};
