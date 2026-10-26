import { useLayoutEffect, useState, type RefObject } from 'react';

// Size the viewport, not the saved Studio canvas. Tall pages retain native scrolling.
export function usePreviewHeight(frame: RefObject<HTMLDivElement>) {
  const [height, setHeight] = useState(240);
  useLayoutEffect(() => {
    const node = frame.current, canvas = node?.parentElement;
    if (!node || !canvas) return;
    let scheduled = 0;
    const measure = () => {
      const box = node.getBoundingClientRect();
      let bottom = box.bottom;
      for (let sibling = node.nextElementSibling; sibling; sibling = sibling.nextElementSibling) {
        const rect = sibling.getBoundingClientRect();
        if (rect.height) bottom = Math.max(bottom, rect.bottom + (parseFloat(getComputedStyle(sibling).marginBottom) || 0));
      }
      const padding = parseFloat(getComputedStyle(canvas).paddingBottom) || 0;
      // Document coordinates prevent page scrolling from growing the preview itself.
      const top = Math.max(0, box.top + window.scrollY);
      const next = Math.max(240, Math.floor(window.innerHeight - top - (bottom - box.bottom) - padding));
      setHeight(previous => previous === next ? previous : next);
    };
    const schedule = () => { cancelAnimationFrame(scheduled); scheduled = requestAnimationFrame(measure); };
    const resize = new ResizeObserver(schedule);
    const observe = () => {
      resize.disconnect();
      resize.observe(document.body);
      resize.observe(canvas);
      for (const child of canvas.children) if (child !== node) resize.observe(child);
      schedule();
    };
    // Status, selection help and save links can appear after the preview mounts.
    const children = new MutationObserver(observe);
    children.observe(canvas, { childList: true });
    observe(); measure();
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(scheduled); resize.disconnect(); children.disconnect();
      window.removeEventListener('resize', schedule);
    };
  }, [frame]);
  return height;
}
