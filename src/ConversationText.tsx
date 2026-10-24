import Markdown from '@splunk/react-ui/Markdown';

/** Model text can format prose, but cannot load images or create navigation. */
export default function ConversationText({ text }: { text: string }) {
  return <Markdown text={text} imageRenderer={({ alt }) => <span>{alt || 'Image reference'}</span>}
    linkRenderer={({ children }) => <span>{children}</span>}/>;
}
