// Type declaration for html2canvas module
// This is optional - the component has SVG fallback if html2canvas is not installed
declare module 'html2canvas' {
  interface Html2CanvasOptions {
    backgroundColor?: string | null;
    scale?: number;
    logging?: boolean;
    useCORS?: boolean;
    allowTaint?: boolean;
    width?: number;
    height?: number;
    x?: number;
    y?: number;
    scrollX?: number;
    scrollY?: number;
    windowWidth?: number;
    windowHeight?: number;
    foreignObjectRendering?: boolean;
    removeContainer?: boolean;
    imageTimeout?: number;
    ignoreElements?: (element: Element) => boolean;
    onclone?: (document: Document) => void;
  }

  function html2canvas(
    element: HTMLElement,
    options?: Html2CanvasOptions
  ): Promise<HTMLCanvasElement>;

  export default html2canvas;
}
