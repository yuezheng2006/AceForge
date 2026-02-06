import React, { useState, useEffect, useRef } from 'react';
import { Layers, Download, Loader2 } from 'lucide-react';
import { toolsApi, preferencesApi } from '../services/api';

const POLL_INTERVAL_MS = 500;
const MODEL_POLL_MS = 800;

interface StemSplittingPanelProps {
  onTracksUpdated?: () => void | Promise<void>;
}

export const StemSplittingPanel: React.FC<StemSplittingPanelProps> = ({ onTracksUpdated }) => {
  const [inputFile, setInputFile] = useState<File | null>(null);
  const [baseFilename, setBaseFilename] = useState('');
  const [stemCount, setStemCount] = useState('4');
  const [mode, setMode] = useState('');
  const [device, setDevice] = useState('auto');
  const [exportFormat, setExportFormat] = useState('wav');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [modelReady, setModelReady] = useState<boolean | null>(null);
  const [modelState, setModelState] = useState('');
  const [modelMessage, setModelMessage] = useState('');
  const [modelDownloadProgress, setModelDownloadProgress] = useState<number | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const modelPollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    toolsApi.stemSplitModelStatus()
      .then((r) => {
        setModelReady(r.ready);
        setModelState(r.state || '');
        setModelMessage(r.message || '');
      })
      .catch(() => setModelReady(false));
  }, []);

  useEffect(() => {
    preferencesApi.get()
      .then((prefs) => {
        const s = prefs.stem_split;
        if (s?.stem_count != null) setStemCount(String(s.stem_count));
        if (s?.mode != null) setMode(s.mode);
        if (s?.device_preference != null) setDevice(s.device_preference);
        if (s?.export_format != null) setExportFormat(s.export_format);
      })
      .catch(() => {});
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
      toolsApi.stemSplitModelStatus()
        .then((r) => {
          setModelReady(r.ready);
          setModelState(r.state || '');
          setModelMessage(r.message || '');
        })
        .catch(() => {});
      toolsApi.getProgress()
        .then((p) => {
          if (p.stage === 'stem_split_model_download') {
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
    if (!loading) return;
    const poll = () => {
      toolsApi.getProgress()
        .then((p) => {
          setProgress(p.fraction);
          if (p.done || p.error) {
            setLoading(false);
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
          }
        })
        .catch(() => {});
    };
    poll();
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [loading]);

  const handleDownloadModels = () => {
    setError(null);
    toolsApi.stemSplitModelEnsure().then(() => {
      setModelState('downloading');
      setModelMessage('Downloading Demucs model (first use only). This may take several minutes.');
    }).catch((e) => setError(e.message));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (!inputFile) {
      setError('Please select an input audio file.');
      return;
    }
    if (modelReady !== true || modelState === 'downloading') {
      setError(modelState === 'downloading' ? 'Please wait for Demucs model download to finish.' : 'Demucs model is not ready. Click Download Demucs models first.');
      return;
    }
    const formData = new FormData();
    formData.append('input_file', inputFile);
    if (baseFilename.trim()) formData.set('base_filename', baseFilename.trim());
    formData.set('stem_count', stemCount);
    formData.set('mode', mode);
    formData.set('device_preference', device);
    formData.set('export_format', exportFormat);
    setLoading(true);
    setProgress(0);
    try {
      const prefs = await preferencesApi.get();
      if (prefs.output_dir) formData.set('out_dir', prefs.output_dir);
      const res = await toolsApi.stemSplit(formData);
      if (res?.error) {
        setError(res.message || 'Stem splitting failed.');
        setLoading(false);
        return;
      }
      await preferencesApi.update({ stem_split: { stem_count: stemCount, mode, device_preference: device, export_format: exportFormat } });
      setSuccess(res?.message || 'Stems saved to output directory.');
      setLoading(false);
      onTracksUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stem splitting failed.');
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col overflow-y-auto p-4 text-zinc-800 dark:text-zinc-200">
      <div className="flex items-center gap-2 mb-4">
        <Layers className="w-6 h-6 text-pink-500" />
        <h2 className="text-lg font-semibold">Stem Splitting</h2>
      </div>
      <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
        Split audio into separate stems (vocals, drums, bass, etc.) using Demucs. Upload an audio file and choose the number of stems.
      </p>

      {modelReady === false && modelState !== 'downloading' && (
        <div className="mb-4 p-3 rounded-lg bg-amber-500/10 text-amber-700 dark:text-amber-400 text-sm">
          <p className="font-medium mb-1">Demucs model is not downloaded yet.</p>
          <p className="mb-2">{modelMessage || 'Click "Download Demucs models" to download it (first use only).'}</p>
          <button
            type="button"
            onClick={handleDownloadModels}
            className="inline-flex items-center gap-1 rounded-lg bg-amber-500 text-white px-3 py-1.5 text-sm font-medium hover:bg-amber-600"
          >
            <Download size={14} /> Download Demucs models
          </button>
        </div>
      )}
      {modelState === 'downloading' && (
        <div className="mb-4 p-3 rounded-lg bg-blue-500/10 text-blue-700 dark:text-blue-400 text-sm">
          <p className="font-medium mb-2 flex items-center gap-2">
            <Loader2 size={16} className="animate-spin" /> Downloading Demucs model…
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
          <label className="block text-sm font-medium mb-1">Input Audio File</label>
          <input
            type="file"
            accept="audio/*,.mp3,.wav,.m4a,.flac,.ogg"
            onChange={(e) => setInputFile(e.target.files?.[0] || null)}
            className="w-full text-sm file:mr-2 file:rounded-lg file:border-0 file:bg-pink-500 file:px-3 file:py-2 file:text-white file:text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Base filename (optional)</label>
          <input
            type="text"
            value={baseFilename}
            onChange={(e) => setBaseFilename(e.target.value)}
            placeholder="Prefix for output filenames"
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Number of Stems</label>
          <select
            value={stemCount}
            onChange={(e) => setStemCount(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          >
            <option value="2">2-Stem (Vocals / Instrumental)</option>
            <option value="4">4-Stem (Vocals, Drums, Bass, Other)</option>
            <option value="6">6-Stem (Vocals, Drums, Bass, Guitar, Piano, Other)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Mode (2-Stem only)</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          >
            <option value="">Standard (All Stems)</option>
            <option value="vocals_only">Acapella (Vocals Only)</option>
            <option value="instrumental">Instrumental / Karaoke</option>
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
          <label className="block text-sm font-medium mb-1">Export Format</label>
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-800 px-3 py-2 text-sm"
          >
            <option value="wav">WAV (Uncompressed)</option>
            <option value="mp3">MP3 (256kbps)</option>
          </select>
        </div>

        {loading && (
          <div className="w-full h-2 rounded-full bg-zinc-200 dark:bg-zinc-700 overflow-hidden">
            <div
              className="h-full bg-pink-500 transition-all duration-300"
              style={{ width: `${Math.min(100, progress * 100)}%` }}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={loading || modelReady !== true || modelState === 'downloading'}
          className="rounded-lg bg-pink-500 text-white px-4 py-2 text-sm font-medium hover:bg-pink-600 disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
        >
          {modelState === 'downloading' ? (
            <><Loader2 size={16} className="animate-spin" /> Downloading Demucs models…</>
          ) : loading ? (
            <><Loader2 size={16} className="animate-spin" /> Splitting…</>
          ) : (
            'Split Stems'
          )}
        </button>
      </form>
    </div>
  );
};
