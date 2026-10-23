import Button from '@splunk/react-ui/Button';
import styled, { createGlobalStyle } from 'styled-components';
import { variables as v } from '@splunk/themes';

export const GlobalStyle = createGlobalStyle`
  #constellation-root, #root { color: ${v.contentColorDefault}; font-family: ${v.fontFamily}; }
  #constellation-root * { box-sizing: border-box; }
  #constellation-root h1, #constellation-root h2, #constellation-root h3 { color: ${v.contentColorDefault}; }
  #constellation-settings input {
    background: transparent; color: ${v.contentColorDefault}; border: 0; box-shadow: none;
    height: auto; padding: 0; margin: 0;
  }
  #constellation-settings input::placeholder { color: ${v.contentColorDefault}; opacity: 1; }
`;
export const Shell = styled.div`
  color: ${v.contentColorDefault}; background: ${v.backgroundColorPage}; min-height: 90vh;
  font-family: ${v.fontFamily}; font-size: ${v.fontSize}; line-height: 1.5;
`;
export const Header = styled.header`
  display: flex; gap: ${v.spacingMedium}; align-items: center; flex-wrap: wrap;
  padding: ${v.spacingMedium} ${v.spacingLarge}; border-bottom: 1px solid ${v.borderColor};
  background: ${v.backgroundColorSection};
  h1 { margin: 0; font-size: ${v.fontSizeLarge}; font-weight: 500; }
`;
export const Actions = styled.div`
  display: flex; gap: ${v.spacingSmall}; align-items: center; flex-wrap: wrap;
`;
export const Workspace = styled.div<{ $floating: boolean }>`
  position: relative; display: grid; grid-template-columns: ${p => p.$floating ? 'minmax(0, 1fr)' : 'minmax(0, 1fr) minmax(300px, 350px)'};
  min-height: 780px;
  @media (max-width: 760px) { grid-template-columns: minmax(0, 1fr); }
`;
export const Canvas = styled.main`
  min-width: 0; padding: ${v.spacingLarge};
  h2 { margin: 0; font-weight: 500; font-size: ${v.fontSizeLarge}; }
`;
export const CanvasHeading = styled.div`
  display: flex; align-items: flex-start; justify-content: space-between; gap: ${v.spacingMedium};
  flex-wrap: wrap; margin-bottom: ${v.spacingLarge};
`;
export const Muted = styled.p`
  color: ${v.contentColorDefault}; font-size: ${v.fontSizeSmall}; margin: ${v.spacingSmall} 0;
`;
export const Conversation = styled.aside<{ $floating: boolean; $collapsed: boolean }>`
  display: ${p => p.$collapsed ? 'none' : 'flex'}; flex-direction: column; gap: ${v.spacingMedium};
  padding: ${v.spacingMedium}; background: ${v.backgroundColorSection}; color: ${v.contentColorDefault};
  border: 1px solid ${v.borderColor}; min-width: 0; z-index: 10;
  position: ${p => p.$floating ? 'fixed' : 'sticky'}; align-self: start; top: ${p => p.$floating ? 'auto' : v.spacingMedium};
  right: ${p => p.$floating ? '20px' : 'auto'}; bottom: ${p => p.$floating ? '20px' : 'auto'};
  width: ${p => p.$floating ? '350px' : 'auto'}; max-width: calc(100% - 16px);
  max-height: calc(100dvh - 32px); overflow: hidden;
  > header, > form, > p { flex-shrink: 0; }
  border-radius: ${p => p.$floating ? v.borderRadius : '0'};
  @media (max-width: 760px) { position: relative; right: auto; bottom: auto; width: auto; max-width: none; }
`;
export const PanelHeading = styled.div`
  display: flex; justify-content: space-between; align-items: center; gap: ${v.spacingSmall}; flex-wrap: wrap;
  h3 { font-size: ${v.fontSize}; margin: 0; font-weight: 500; }
`;
export const Message = styled.div<{ $user?: boolean }>`
  background: ${p => p.$user ? v.backgroundColorPage : v.backgroundColorSection};
  color: ${v.contentColorDefault}; padding: ${v.spacingSmall}; border-radius: ${v.borderRadius};
  overflow-wrap: anywhere;
`;
export const Transcript = styled.div`
  display: flex; flex-direction: column; gap: ${v.spacingSmall};
  min-height: 0; flex-shrink: 0;
`;
export const Composer = styled.form`
  flex-shrink: 0; display: flex; flex-direction: column; gap: ${v.spacingSmall};
`;
export const FloatingLauncher = styled.div`
  position: absolute; bottom: ${v.spacingLarge}; right: ${v.spacingLarge}; z-index: 11;
`;
export const RendererFrame = styled.div`
  position:relative; min-height: 650px; width: 100%; overflow: hidden; border-radius: ${v.borderRadius};
`;
export const Source = styled.pre`
  color: ${v.contentColorDefault};
  white-space: pre-wrap; overflow-wrap: anywhere; max-height: 60vh; overflow: auto;
  font-size: ${v.fontSizeSmall}; background: ${v.backgroundColorPage}; padding: ${v.spacingMedium};
`;

export const EmptyCanvas = styled.section<{ $floating: boolean }>`
  min-height: 650px; display: flex; flex-direction: column; justify-content: center;
  max-width: 820px; margin: 0 auto; padding: ${v.spacingLarge} 0;
  h2 { font-size: ${v.fontSizeXXLarge}; line-height: 1.2; margin: 0 0 ${v.spacingMedium}; }
  > p { max-width: 560px; }
  ${p => p.$floating ? 'margin-right: 380px;' : ''}
  @media (max-width: 760px) { min-height: 380px; margin: 0; }
`;
export const IdeaGrid = styled.div`
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: ${v.spacingMedium};
  margin: ${v.spacingLarge} 0;
  @media (max-width: 520px) { grid-template-columns: minmax(0, 1fr); }
`;
export const IdeaText = styled.span`
  display: block; white-space: normal; text-align: left;
  strong { display: block; margin-bottom: ${v.spacingSmall}; font-weight: 600; }
  span { display: block; font-size: ${v.fontSizeSmall}; font-weight: 400; line-height: 1.5; }
`;
export const PromptChoices = styled.div`
  display: flex; flex-direction: column; gap: ${v.spacingSmall};
  > p { color: ${v.contentColorDefault}; margin: 0; font-size: ${v.fontSizeSmall}; font-weight: 600; }
`;

export const IdeaButton = styled(Button)`
  && { height: auto; padding: ${v.spacingLarge}; white-space: normal; text-align: left; }
`;

export const ConversationScroll = styled.div`
  flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column;
  gap: ${v.spacingMedium}; padding-right: ${v.spacingXSmall};
`;

export const LibraryRow = styled.div`
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: ${v.spacingSmall}; padding: ${v.spacingMedium} 0; border-bottom: 1px solid ${v.borderColor};
  > div:first-child { min-width: 0; overflow-wrap: anywhere; }
`;
