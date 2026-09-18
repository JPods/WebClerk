/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React from "react";

type State = { hasError: boolean; error?: Error };

export default class ErrorBoundary extends React.Component<{
  children: React.ReactNode;
  fallback?: React.ReactNode;
}, State> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: any) {
    // Log to console or external service
    // eslint-disable-next-line no-console
    console.error("ErrorBoundary caught error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <div className="font-semibold text-red-700">Something went wrong rendering this component.</div>
          <div className="text-sm text-gray-600 mt-2">{this.props.fallback || "Try refreshing or contact support."}</div>
        </div>
      );
    }

    return this.props.children as any;
  }
}
