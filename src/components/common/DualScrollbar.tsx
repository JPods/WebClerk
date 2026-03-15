/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * DualScrollbar - Provides a synchronized scrollbar at the top of the content
 * 
 * Renders a scrollbar at the top that syncs with the content's natural bottom scrollbar.
 * Used to provide easy access to horizontal scrolling in wide components like Gantt charts.
 */
import { useEffect, useRef, useState, useCallback, type ReactNode, type FC } from "react";

interface DualScrollbarProps {
  children: ReactNode;
  /** CSS selector to find the scrollable container within children (default: first overflow-auto element) */
  scrollSelector?: string;
  /** Class name for the outer wrapper */
  className?: string;
  /** Whether to show the top scrollbar (default: true) */
  showTopScrollbar?: boolean;
}

export const DualScrollbar: FC<DualScrollbarProps> = ({
  children,
  scrollSelector,
  className = "",
  showTopScrollbar = true,
}) => {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const topScrollRef = useRef<HTMLDivElement>(null);
  const topScrollInnerRef = useRef<HTMLDivElement>(null);
  const [scrollWidth, setScrollWidth] = useState(0);
  const [clientWidth, setClientWidth] = useState(0);
  const isScrollingRef = useRef<"top" | "content" | null>(null);

  // Find the scrollable container within the children
  const getScrollContainer = useCallback((): HTMLElement | null => {
    if (!wrapperRef.current) return null;
    
    if (scrollSelector) {
      return wrapperRef.current.querySelector(scrollSelector);
    }
    
    // Default: look for SVAR Gantt's internal scroll container
    // SVAR Gantt uses .wx-chart for the horizontal timeline scroll
    const svarChart = wrapperRef.current.querySelector(".wx-chart");
    if (svarChart) return svarChart as HTMLElement;
    
    // Fallback: look for any overflow-auto element
    const overflowAuto = wrapperRef.current.querySelector('[class*="overflow-auto"], [style*="overflow"]');
    if (overflowAuto) return overflowAuto as HTMLElement;
    
    return null;
  }, [scrollSelector]);

  // Update the top scrollbar width to match content width
  const updateScrollWidth = useCallback(() => {
    const scrollContainer = getScrollContainer();
    if (!scrollContainer || !topScrollInnerRef.current) return;
    
    const newScrollWidth = scrollContainer.scrollWidth;
    const newClientWidth = scrollContainer.clientWidth;
    
    if (newScrollWidth !== scrollWidth || newClientWidth !== clientWidth) {
      setScrollWidth(newScrollWidth);
      setClientWidth(newClientWidth);
      topScrollInnerRef.current.style.width = `${newScrollWidth}px`;
    }
  }, [getScrollContainer, scrollWidth, clientWidth]);

  // Sync top scrollbar with content scroll
  const handleContentScroll = useCallback(() => {
    if (isScrollingRef.current === "top") return;
    
    const scrollContainer = getScrollContainer();
    if (!scrollContainer || !topScrollRef.current) return;
    
    isScrollingRef.current = "content";
    topScrollRef.current.scrollLeft = scrollContainer.scrollLeft;
    requestAnimationFrame(() => { isScrollingRef.current = null; });
  }, [getScrollContainer]);

  // Sync content scroll with top scrollbar
  const handleTopScroll = useCallback(() => {
    if (isScrollingRef.current === "content") return;
    
    const scrollContainer = getScrollContainer();
    if (!scrollContainer || !topScrollRef.current) return;
    
    isScrollingRef.current = "top";
    scrollContainer.scrollLeft = topScrollRef.current.scrollLeft;
    requestAnimationFrame(() => { isScrollingRef.current = null; });
  }, [getScrollContainer]);

  // Set up scroll event listeners and resize observer
  useEffect(() => {
    if (!showTopScrollbar) return;

    const scrollContainer = getScrollContainer();
    if (!scrollContainer) return;

    // Initial width update
    updateScrollWidth();

    // Listen for scroll events on the content
    scrollContainer.addEventListener("scroll", handleContentScroll);

    // Watch for size changes
    const resizeObserver = new ResizeObserver(() => {
      updateScrollWidth();
    });
    resizeObserver.observe(scrollContainer);

    // Also observe mutations in case content changes
    const mutationObserver = new MutationObserver(() => {
      setTimeout(updateScrollWidth, 100);
    });
    mutationObserver.observe(scrollContainer, { 
      childList: true, 
      subtree: true,
      attributes: true,
      attributeFilter: ["style", "class"],
    });

    return () => {
      scrollContainer.removeEventListener("scroll", handleContentScroll);
      resizeObserver.disconnect();
      mutationObserver.disconnect();
    };
  }, [showTopScrollbar, getScrollContainer, updateScrollWidth, handleContentScroll]);

  // Retry finding scroll container after initial render
  useEffect(() => {
    if (!showTopScrollbar) return;
    
    // SVAR Gantt may not be fully rendered on first mount - use longer retry intervals
    const retryTimeouts = [50, 100, 200, 400, 800, 1500, 3000, 5000];
    const timeoutIds = retryTimeouts.map((delay) =>
      setTimeout(() => {
        updateScrollWidth();
      }, delay)
    );
    
    // Also observe wrapper for async content loading (Gantt mounts after data loads)
    let wrapperObserver: MutationObserver | null = null;
    if (wrapperRef.current) {
      wrapperObserver = new MutationObserver(() => {
        setTimeout(updateScrollWidth, 50);
      });
      wrapperObserver.observe(wrapperRef.current, {
        childList: true,
        subtree: true,
      });
    }

    return () => {
      timeoutIds.forEach(clearTimeout);
      wrapperObserver?.disconnect();
    };
  }, [showTopScrollbar, updateScrollWidth]);

  // Only show top scrollbar when there's actually horizontal overflow
  const hasHorizontalScroll = scrollWidth > clientWidth;

  return (
    <div className={`flex flex-col ${className}`}>
      {/* Top scrollbar - only visible when content overflows horizontally */}
      {showTopScrollbar && (
        <div
          ref={topScrollRef}
          onScroll={handleTopScroll}
          className={`flex-shrink-0 overflow-x-auto overflow-y-hidden border-b border-gray-200 bg-gray-50 transition-opacity dark:border-gray-700 dark:bg-gray-800/50 ${
            hasHorizontalScroll ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
          style={{ height: hasHorizontalScroll ? "14px" : "0px" }}
        >
          <div
            ref={topScrollInnerRef}
            style={{ width: scrollWidth || 1, height: "1px" }}
          />
        </div>
      )}
      
      {/* Content - overflow-y-auto enables vertical scroll, min-h-0 allows shrinking */}
      <div ref={wrapperRef} className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {children}
      </div>
    </div>
  );
};

export default DualScrollbar;
