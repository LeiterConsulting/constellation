import { createRoot } from 'react-dom/client';
import App from './App';
import { getThemeOptions, getUserTheme } from '@splunk/splunk-utils/themes';
import { isSplunk } from './api';

const mount = async () => {
  const target = document.getElementById('constellation-root') || document.getElementById('root');
  if (!target || target.dataset.mounted) return;
  target.dataset.mounted = 'true';
  let colorScheme: 'light' | 'dark' = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  if (isSplunk()) {
    try { colorScheme = getThemeOptions(await getUserTheme()).colorScheme; }
    catch { colorScheme = 'light'; }
  }
  createRoot(target).render(<App initialColorScheme={colorScheme}/>);
};
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
else mount();
