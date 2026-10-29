import { Component, lazy, Suspense, type ComponentProps, type ReactNode } from 'react';
import { Muted } from './styles';

// The renderer is unnecessary on a blank canvas or while configuring a model.
const DashboardPreview = lazy(() => import('./Preview'));
type Props = ComponentProps<typeof import('./Preview')['default']>;

class PreviewLoadBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { /* Do not log document content or native errors. */ }
  render() {
    return this.state.failed
      ? <Muted role="alert">The preview could not load. Your dashboard and conversation remain available. Refresh this tab to try again.</Muted>
      : this.props.children;
  }
}

export default function PreviewLoader(props: Props) {
  return <PreviewLoadBoundary key={props.documentId}>
    <Suspense fallback={<Muted role="status">Loading dashboard preview…</Muted>}><DashboardPreview {...props}/></Suspense>
  </PreviewLoadBoundary>;
}
