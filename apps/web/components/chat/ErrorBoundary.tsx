"use client";

import { Component, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="flex flex-col items-center gap-2 p-4 text-center">
          <p className="text-sm text-zinc-400">Something went wrong.</p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false })}
            className="text-xs text-amber-500 hover:text-amber-400 underline"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
