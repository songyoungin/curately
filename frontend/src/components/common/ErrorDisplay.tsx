import { AlertCircle } from 'lucide-react';

interface ErrorDisplayProps {
  message: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ message, onRetry }: ErrorDisplayProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-8">
      <AlertCircle className="w-10 h-10 text-rose-500" />
      <p className="text-gray-700 text-center">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg bg-rose-50 px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-100 transition-colors"
        >
          Try Again
        </button>
      )}
    </div>
  );
}
