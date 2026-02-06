import React, { useEffect, useRef, useState } from 'react';
import { X, Copy } from 'lucide-react';

interface ConsolePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const LOG_STREAM_URL = '/logs/stream';

export const ConsolePanel: React.FC<ConsolePanelProps> = ({ isOpen, onClose }) => {
  const [lines, setLines] = useState<string[]>([]);
  const [status, setStatus] = useState<'connecting' | 'connected' | 'closed' | 'error'>('closed');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    setLines(prev => [...prev, `[Console] Connecting to ${LOG_STREAM_URL}...`]);
    setStatus('connecting');
    setErrorMessage(null);

    const base = window.location.origin;
    const url = `${base}${LOG_STREAM_URL}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus('connected');
      setLines(prev => [...prev, '[System] Log stream connected.']);
    };

    es.onmessage = (event: MessageEvent) => {
      const msg = event.data;
      if (msg != null && typeof msg === 'string') {
        setLines(prev => {
          const next = [...prev, msg];
          if (next.length > 2000) return next.slice(-1500);
          return next;
        });
      }
    };

    es.onerror = () => {
      if (es.readyState === EventSource.CLOSED) {
        setStatus('closed');
      } else {
        setStatus('error');
        setErrorMessage('Connection lost. Reconnecting...');
      }
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [isOpen]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  const copyToClipboard = () => {
    const text = lines.join('\n');
    if (!text) return;
    navigator.clipboard.writeText(text).then(
      () => setErrorMessage(null),
      () => setErrorMessage('Copy failed')
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-black/80 backdrop-blur-sm">
      <div className="flex flex-col flex-1 min-h-0 m-4 rounded-xl overflow-hidden bg-zinc-900 border border-zinc-700 shadow-2xl">
        <div className="flex items-center justify-between px-4 py-2 bg-zinc-800 border-b border-zinc-700">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-zinc-200">Console</span>
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                status === 'connected'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : status === 'connecting'
                    ? 'bg-amber-500/20 text-amber-400'
                    : status === 'error'
                      ? 'bg-red-500/20 text-red-400'
                      : 'bg-zinc-600 text-zinc-400'
              }`}
            >
              {status}
            </span>
            {errorMessage && (
              <span className="text-xs text-amber-400">{errorMessage}</span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={copyToClipboard}
              className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
              title="Copy all to clipboard"
            >
              <Copy size={18} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
              title="Close"
            >
              <X size={20} />
            </button>
          </div>
        </div>
        <div
          className="flex-1 overflow-auto p-3 font-mono text-xs text-zinc-300 whitespace-pre-wrap break-words select-text cursor-text"
          style={{ userSelect: 'text', WebkitUserSelect: 'text' }}
        >
          {lines.map((line, i) => (
            <div key={i} className="leading-relaxed select-text">
              {line}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </div>
  );
};
