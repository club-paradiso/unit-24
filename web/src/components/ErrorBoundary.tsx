import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unit-24 crashed", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="main stack" role="alert">
        <h1>문제가 생겼습니다 · Something went wrong</h1>
        <p>화면을 표시하지 못했습니다. 저장된 학습 기록은 그대로입니다. · The page could not be displayed. Your saved progress has not been changed.</p>
        <p className="muted small">{this.state.error.message}</p>
        <p>
          <a className="btn btn-primary" href="/">
            다시 불러오기 · Reload
          </a>
        </p>
      </div>
    );
  }
}
