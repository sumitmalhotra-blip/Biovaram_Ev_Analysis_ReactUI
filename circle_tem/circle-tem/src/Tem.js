import { useEffect, useState } from "react";
import ImageCanvas from "./ImageCanvas";
import BoxPopup from "./Boxpopup";

const API = "http://localhost:8000";
const userId = localStorage.getItem("loginUserId");

function Tem() {
  const [images, setImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [selectedBox, setSelectedBox] = useState(null);
  const [hoverId, setHoverId] = useState(null);
  const [loading, setLoading] = useState(false);
const [loadingImageId, setLoadingImageId] = useState(null);


  // 🔹 Load images
 useEffect(() => {
  fetch(`${API}/images/${userId}`)
    .then(res => res.json())
    .then(data => {
      const list = Object.entries(data).map(([id, img]) => ({
        image_id: id,
        image_url: img.image_url,
        boxes: img.boxes || []   // ✅ correct field
      }));
      setImages(list);
    });
}, []);


  // 🔹 Upload images
 const uploadImage = async (e) => {
  const files = Array.from(e.target.files);
  if (!files.length) return;

  setLoading(true);

  try {
    const formData = new FormData();
    files.forEach(f => formData.append("files", f));

    const res = await fetch(`${API}/upload-multiple-images/${userId}`, {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    setImages(prev => [...data, ...prev]);
  } catch (err) {
    console.error(err);
  } finally {
    setLoading(false);
  }
};


  // 🔹 Create new circle
  const handleCreateBox = (x, y) => {
    const r = 20;
    const circle = {
      cx: x,
      cy: y,
      r,
      diameter_nm: r * 2,
      viability: "review"
    };

    setSelectedImage(prev => ({
      ...prev,
      boxes: [...prev.boxes, circle]
    }));
  };

  // 🔹 Save popup edit
  const handleSaveBox = (updated) => {
    setSelectedImage(prev => ({
      ...prev,
      boxes: prev.boxes.map(b => (b === selectedBox ? updated : b))
    }));
    setSelectedBox(null);
  };

  // 🔹 Delete image
  const handleDeleteImage = async (imageId) => {
    await fetch(`${API}/images/${userId}/${imageId}`, { method: "DELETE" });

    setImages(prev => prev.filter(img => img.image_id !== imageId));

    if (selectedImage?.image_id === imageId) {
      setSelectedImage(null);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: "#f5f6fa" }}>
      {/* 🔹 SIDEBAR */}
      <div style={{ width: 220, padding: 10, background: "#fff", borderRight: "1px solid #ddd",height:'95%', overflowY:'auto' }}>
       <div
  style={{
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 12px",
    borderBottom: "1px solid #e0e0e0",
  }}
>
  <h4 style={{ margin: 0 }}>Images</h4>

  <label
    style={{
      backgroundColor: "#1976d2",
      color: "#fff",
      padding: "6px 14px",
      borderRadius: "6px",
      cursor: "pointer",
      fontSize: "14px",
    }}
  >
    + Upload
    <input type="file" multiple hidden onChange={uploadImage} />
  </label>
</div>


        {images.map(img => (
          <div
            key={img.image_id}
            style={{ position: "relative", marginBottom: 12,marginTop:'10px' }}
            onMouseEnter={() => setHoverId(img.image_id)}
            onMouseLeave={() => setHoverId(null)}
          >
            <img
              src={`${API}${img.image_url}`}
              width="190"
              alt=""
              style={{
                cursor: "pointer",
                border: selectedImage?.image_id === img.image_id
                  ? "2px solid blue"
                  : "1px solid #ccc",
                borderRadius: 6,
              }}
              onClick={() =>
  setSelectedImage({
    image_id: img.image_id,
    image_url: img.image_url,
    boxes: JSON.parse(JSON.stringify(img.boxes)) // 🔥 force deep copy
  })
}

            />
{loading && (
  <div style={{
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(255,255,255,0.7)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 6,
    fontSize: 14,
    fontWeight: 500
  }}>
    Uploading...
  </div>
)}

            {hoverId === img.image_id && (
              <div style={{
                position: "absolute",
                top: 5,
                right: 5,
                background: "rgba(0,0,0,0.6)",
                padding: "4px 6px",
                borderRadius: 4
              }}>
                <span
                  style={{ color: "#fff", cursor: "pointer" }}
                  onClick={() => handleDeleteImage(img.image_id)}
                >
                  🗑
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 🔹 CANVAS */}
      <div style={{ flex: 1, padding: 10 }}>
        {selectedImage && (
          <ImageCanvas
            imageId={selectedImage.image_id}
            imageUrl={`${API}${selectedImage.image_url}`}
            boxes={selectedImage.boxes}
            setBoxes={(boxes) => {
              setSelectedImage(prev => ({ ...prev, boxes }));
              setImages(prev =>
                prev.map(i =>
                  i.image_id === selectedImage.image_id
                    ? { ...i, boxes }
                    : i
                )
              );
            }}
            onCreateBox={handleCreateBox}
            onSelectBox={setSelectedBox}
          />
        )}
      </div>

      {selectedBox && (
        <BoxPopup
          box={selectedBox}
          onClose={() => setSelectedBox(null)}
          onSave={handleSaveBox}
        />
      )}
    </div>
  );
}

export default Tem;
