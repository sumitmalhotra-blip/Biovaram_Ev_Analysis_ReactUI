import { useRef, useState } from "react";
import "../../App.css";
type SimpleMark = {
  x: number;
  y: number;
};

type RulerMark = {
  id: number;
  x: number;
  y: number;
  kda: string;
  concentration: string;
};

type Props = {
  imageUrl: string;
  markMode: boolean;
  topBottomMarks: SimpleMark[];
  detectedRulerMarks: RulerMark[];
  onAddMark: (x: number, y: number) => void;
};

function RulerMarker({
  imageUrl,
  markMode,
  topBottomMarks,
  detectedRulerMarks,
  onAddMark,
}: Props) {
  const imgRef = useRef<HTMLImageElement | null>(null);
  const [displaySize, setDisplaySize] = useState({ width: 0, height: 0 });

  const handleImageLoad = () => {
    if (!imgRef.current) return;
    setDisplaySize({
      width: imgRef.current.clientWidth,
      height: imgRef.current.clientHeight,
    });
  };

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!markMode || !imgRef.current) return;
    if (topBottomMarks.length >= 2) return;

    const rect = imgRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    if (
      clickX < 0 ||
      clickY < 0 ||
      clickX > rect.width ||
      clickY > rect.height
    ) {
      return;
    }

    const x = Math.round((clickX / rect.width) * imgRef.current.naturalWidth);
    const y = Math.round((clickY / rect.height) * imgRef.current.naturalHeight);

    onAddMark(x, y);
  };

  const getOverlayPosition = (x: number, y: number) => {
    if (!imgRef.current || !displaySize.width || !displaySize.height) {
      return { left: 0, top: 0 };
    }

    const left = (x / imgRef.current.naturalWidth) * displaySize.width;
    const top = (y / imgRef.current.naturalHeight) * displaySize.height;

    return { left, top };
  };

  return (
    <div className="marker-card">
      <div className="marker-instruction">
        {markMode
          ? topBottomMarks.length === 0
            ? "Click the TOP ruler band on lane 0"
            : "Click the BOTTOM ruler band on lane 0"
          : "Lane 0 markers will appear on the image"}
      </div>

      <div className="marker-stage" onClick={handleClick}>
        <img
          ref={imgRef}
          src={imageUrl}
          alt="Lane 0 marking"
          className="marker-image"
          onLoad={handleImageLoad}
        />

        {topBottomMarks.map((mark, index) => {
          const pos = getOverlayPosition(mark.x, mark.y);

          return (
            <div
              key={`tb-${index}`}
              className={`overlay-badge ${index === 0 ? "top-badge" : "bottom-badge"}`}
              style={{
                left: `${pos.left}px`,
                top: `${pos.top}px`,
              }}
            >
              {index === 0 ? "Top" : "Bottom"}
            </div>
          );
        })}

        {detectedRulerMarks.map((mark) => {
          const pos = getOverlayPosition(mark.x, mark.y);

          return (
            <div
              key={mark.id}
              className="overlay-badge ruler-badge"
              style={{
                left: `${pos.left}px`,
                top: `${pos.top}px`,
              }}
            >
              R{mark.id}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default RulerMarker;