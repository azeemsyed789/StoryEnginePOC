import React, { useState, useRef, useEffect } from "react";
import {
  DndContext,
  useDraggable,
  useSensor,
  useSensors,
  PointerSensor,
} from "@dnd-kit/core";
import axios from "axios";

// --- CONFIG ---
const BASE_URL = "http://127.0.0.1:8000";

// --- PRE-LOADED ASSETS ---
const PRELOADED_BACKGROUNDS = [
  {
    id: "bg1",
    filename: "backgrounds/bg1.png",
    name: "Forest",
    url: `${BASE_URL}/static/uploads/backgrounds/bg1.png`,
  },
  {
    id: "bg2",
    filename: "backgrounds/bg2.png",
    name: "Forest Temple",
    url: `${BASE_URL}/static/uploads/backgrounds/bg2.png`,
  },
  {
    id: "bg3",
    filename: "backgrounds/bg3.png",
    name: "Stone Circle",
    url: `${BASE_URL}/static/uploads/backgrounds/bg3.png`,
  },
  {
    id: "bg4",
    filename: "backgrounds/bg4.png",
    name: "Dark Castle",
    url: `${BASE_URL}/static/uploads/backgrounds/bg4.png`,
  },
  {
    id: "bg5",
    filename: "backgrounds/bg5.png",
    name: "Floating Islands",
    url: `${BASE_URL}/static/uploads/backgrounds/bg5.png`,
  },
];

const PRELOADED_CHARACTERS = [
  {
    id: "sec1",
    filename: "characters/sec1.png",
    name: "Secondary Character 1",
    url: `${BASE_URL}/static/uploads/characters/sec1.png`,
  },
  {
    id: "sec2",
    filename: "characters/sec2.png",
    name: "Secondary Character 2",
    url: `${BASE_URL}/static/uploads/characters/sec2.png`,
  },
];

// --- INITIAL STATE ---
const INITIAL_PAGES = Array(5)
  .fill(null)
  .map((_, i) => ({
    id: i,
    background: null,
    items: [],
    text: `Page ${i + 1} Story Text...`,
    primaryPose: "Standing Naturally",
    secondaryPose: "Standing Naturally",
  }));

// --- DRAGGABLE ITEM ---
function DraggableItem({ id, x, y, image, type, pose, onRemove }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id });

  const style = {
    position: "absolute",
    left: x,
    top: y,
    transform: transform
      ? `translate3d(${transform.x}px, ${transform.y}px, 0)`
      : undefined,
    zIndex: type === "placeholder" ? 100 : 10,
    touchAction: "none",
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      onContextMenu={(e) => {
        e.preventDefault();
        onRemove(id);
      }}
      className="cursor-move w-32 h-40 group hover:scale-105 transition-transform"
    >
      <div
        className={`w-full h-full p-2 flex flex-col items-center justify-center rounded-lg shadow-xl ${
          type === "placeholder"
            ? "bg-cyan-900/80 border-2 border-dashed border-cyan-400"
            : ""
        }`}
      >
        <img
          src={image}
          className="w-full h-full object-contain drop-shadow-2xl pointer-events-none"
        />
        <div className="absolute -bottom-8 w-40 text-center bg-black/90 text-white text-[9px] py-1 px-2 rounded border border-gray-600 z-50">
          <span
            className={
              type === "placeholder"
                ? "text-cyan-400 font-bold"
                : "text-purple-400 font-bold"
            }
          >
            {type === "placeholder" ? "PRIMARY" : "SECONDARY"}
          </span>
          <br />
          <span className="text-white font-bold">{pose}</span>
        </div>
      </div>
    </div>
  );
}

// --- MAIN PANEL ---
export default function BuilderAndUserPanel({ role, onLogout }) {
  const isAdmin = role === "admin";
  const [pages, setPages] = useState(INITIAL_PAGES);
  const [activePageIdx, setActivePageIdx] = useState(0);
  const [backgrounds, setBackgrounds] = useState(PRELOADED_BACKGROUNDS);
  const [characters, setCharacters] = useState(PRELOADED_CHARACTERS);
  const [userFace, setUserFace] = useState(null);
  const [userFaces, setUserFaces] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploadingFace, setIsUploadingFace] = useState(false);
  const [isUploadingCharacter, setIsUploadingCharacter] = useState(false);
  const [storyResult, setStoryResult] = useState(null);
  const [designUserId, setDesignUserId] = useState(null);

  const bgInput = useRef(null);
  const charInput = useRef(null);
  const faceInput = useRef(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );
  const activePage = pages[activePageIdx];
  const token = localStorage.getItem("token");

  const updateActivePage = (updates) => {
    setPages((prev) => {
      const copy = [...prev];
      copy[activePageIdx] = { ...copy[activePageIdx], ...updates };
      return copy;
    });
  };

  const updatePoseAndItems = (poseType, poseValue) => {
    setPages((prev) => {
      const copy = [...prev];
      const pageUpdate = { ...copy[activePageIdx] };

      if (poseType === "primary") pageUpdate.primaryPose = poseValue;
      else pageUpdate.secondaryPose = poseValue;

      pageUpdate.items = pageUpdate.items.map((item) => {
        if (poseType === "primary" && item.type === "placeholder")
          return { ...item, pose: poseValue };
        if (poseType === "secondary" && item.type === "secondary")
          return { ...item, pose: poseValue };
        return item;
      });

      copy[activePageIdx] = pageUpdate;
      return copy;
    });
  };

  useEffect(() => {
    const fetchFaces = async () => {
      try {
        const res = await axios.get(`${BASE_URL}/user-faces`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        });
        console.log("user faces:", res.data);
        setUserFaces(res.data);

        // if (!isAdmin && res.data.length > 0) {
        //   setUserFace(res.data[0]);
        // }
      } catch (err) {
        console.error("Error fetching faces:", err);
      }
    };
    fetchFaces();
  }, [isAdmin]);

  useEffect(() => {
    const fetchSavedDesign = async () => {
      if (isAdmin) return;
      try {
        const res = await axios.get(`${BASE_URL}/user-design`, {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        });
        const faceFile = res.data.user_face_filename;
        const loadedUserFace = {
          filename: faceFile,
          url: `${BASE_URL}/static/uploads/${faceFile}`,
        };
        // Keep the saved face for story generation, but do NOT treat it as
        // "uploaded this session" so the UI doesn't show a preset face image.
        // setUserFace(loadedUserFace);

        const mappedPages = (res.data.pages || []).map((p, idx) => {
          const backgroundAsset = p.background_filename
            ? {
                id: p.background_filename,
                filename: p.background_filename,
                url: `${BASE_URL}/static/uploads/${p.background_filename}`,
              }
            : null;

          return {
            id: idx,
            background: backgroundAsset,
            items: (p.elements || []).map((item, itemIdx) => {
              const filename =
                item.type === "placeholder"
                  ? faceFile
                  : item.asset_filename || item.filename;
              return {
                id: `${item.type}_${itemIdx}_${Date.now()}`,
                filename,
                image: `${BASE_URL}/static/uploads/${filename}`,
                url: `${BASE_URL}/static/uploads/${filename}`,
                x: (item.x || 0) * 800,
                y: (item.y || 0) * 600,
                pose: item.pose,
                type: item.type === "character" ? "secondary" : item.type,
              };
            }),
            text: p.text,
            primaryPose:
              p.primary_pose || p.primaryPose || "Standing Naturally",
            secondaryPose:
              p.secondary_pose || p.secondaryPose || "Standing Naturally",
          };
        });

        if (mappedPages.length > 0) {
          setPages(mappedPages);
        }
      } catch (err) {
        if (err.response?.status !== 404) {
          console.error("Error loading saved design", err);
        }
      }
    };

    fetchSavedDesign();
  }, [isAdmin]);

  const handleUpload = async (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      console.log("TOKEN:", token);

      if (type === "bg") {
        formData.append("subdir", "backgrounds");
        const res = await axios.post(`${BASE_URL}/upload-asset`, formData, {
          headers: { Authorization: `Bearer ${token}` },
        });

        const asset = {
          id: res.data.filename,
          url: res.data.url,
          filename: res.data.filename,
          name: file.name,
        };

        setBackgrounds((prev) => [...prev, asset]);
      } else if (type === "char") {
        setIsUploadingCharacter(true);
        formData.append("subdir", "characters");
        try {
          const res = await axios.post(`${BASE_URL}/upload-asset`, formData, {
            headers: { Authorization: `Bearer ${token}` },
          });

          const asset = {
            id: res.data.filename,
            url: res.data.url,
            filename: res.data.filename,
            name: file.name,
          };
          setCharacters((prev) => [...prev, asset]);
        } finally {
          setIsUploadingCharacter(false);
        }
      } else if (type === "face") {
        setIsUploadingFace(true);
        try {
          const faceForm = new FormData();
          faceForm.append("file", file);
          const token = localStorage.getItem("token");
          const headers = token ? { Authorization: `Bearer ${token}` } : {};

          const res = await axios.post(`${BASE_URL}/upload-face`, faceForm, {
            headers,
          });
          const asset = {
            id: res.data.filename,
            url: res.data.url,
            filename: res.data.filename,
            name: file.name,
          };
          setUserFace(asset);
        } catch (err) {
          console.warn(
            "upload-face failed:",
            err.response?.status,
            err.response?.data || err.message
          );
          if (err.response?.status === 401) {
            alert(
              "Face saved locally but server-side face upload requires authentication. Please login to save face to your account."
            );
          } else {
            console.warn(
              "Server face upload failed. Check console for details."
            );
          }
        } finally {
          setIsUploadingFace(false);
        }
      }
    } catch (err) {
      console.error("Upload Failed:", err.response?.data || err.message);
      alert("Upload Failed. Check console for details.");
    }
  };

  const addItem = (asset, type) => {
    console.log("designUserId:", designUserId);
    console.log("asset:", asset);
    console.log("asset.user_id:", asset.user_id);
    const poseToUse =
      type === "placeholder"
        ? activePage.primaryPose
        : activePage.secondaryPose;
    const newItem = {
      id: `${type}_${Date.now()}_${Math.random()}`,
      ...asset,
      image: asset.url || asset.image,
      x: 350 + Math.random() * 30,
      y: 250 + Math.random() * 30,
      pose: poseToUse,
      type: type === "character" ? "secondary" : type,
    };
    updateActivePage({ items: [...activePage.items, newItem] });
  };

  const removeItem = (id) =>
    updateActivePage({ items: activePage.items.filter((i) => i.id !== id) });

  const saveDesign = async () => {
    if (!designUserId) {
      alert("Select a user's face to attach this design to.");
      return;
    }

    const validPages = pages.filter((p) => p.background !== null);
    if (validPages.length === 0) {
      alert("Add at least one background before saving.");
      return;
    }

    if (!userFace) {
      alert("Pick which user's face this design belongs to.");
      return;
    }

    const payload = {
      target_user_id: designUserId,
      user_face_filename: userFace.filename,
      pages: pages.map((p) => ({
        background_filename: p.background ? p.background.filename : "",
        text: p.text,
        primary_pose: p.primaryPose,
        secondary_pose: p.secondaryPose,
        elements: p.items.map((item) => ({
          type: item.type,
          asset_filename:
            item.type === "placeholder" ? userFace.filename : item.filename,
          pose: item.pose,
          x: Math.max(0, Math.min(item.x, 800)) / 800,
          y: Math.max(0, Math.min(item.y, 600)) / 600,
        })),
      })),
      status: "draft",
    };

    try {
      await axios.post(`${BASE_URL}/admin/save-design`, payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      alert("Design saved for user.");
    } catch (err) {
      console.error(err);
      alert("Failed to save design.");
    }
  };

  const handleDragEnd = (e) => {
    const { active, delta } = e;
    if (!delta) return;

    const newItems = activePage.items.map((item) => {
      if (item.id === active.id)
        return { ...item, x: item.x + delta.x, y: item.y + delta.y };
      return item;
    });

    updateActivePage({ items: newItems });
  };

  const generateStory = async () => {
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};
    const hasDesignedPages = pages.some((p) => p.background !== null);

    // If the user has no local design (likely after re-login), rely on server-saved design
    console.log("hasDesignedPages", hasDesignedPages);
    const shouldUseSavedDesign = !hasDesignedPages;

    if (!shouldUseSavedDesign && !userFace) {
      return alert("User: Please upload your face first!");
    }

    setIsGenerating(true);
    try {
      console.log("shouldUseSavedDesign", shouldUseSavedDesign);
      const payload = shouldUseSavedDesign
        ? {}
        : {
            user_face_filename: userFace.filename,
            pages: pages.map((p) => ({
              background_filename: p.background ? p.background.filename : "",
              text: p.text,
              primary_pose: p.primaryPose,
              secondary_pose: p.secondaryPose,
              elements: p.items.map((item) => ({
                type: item.type,
                asset_filename:
                  item.type === "placeholder"
                    ? userFace.filename
                    : item.filename,
                pose: item.pose,
                x: Math.max(0, Math.min(item.x, 800)) / 800,
                y: Math.max(0, Math.min(item.y, 600)) / 600,
              })),
            })),
          };

      const res = await axios.post(`${BASE_URL}/generate-story`, payload, {
        headers: authHeaders,
      });
      setStoryResult(res.data);
    } catch (e) {
      console.error(e);
      alert("Generation Error");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white font-sans overflow-hidden">
      {/* SIDEBAR */}
      <div className="w-[450px] bg-gray-800 border-r border-gray-700 flex flex-col z-20 shadow-2xl">
        {isAdmin ? (
          <div className="p-5 overflow-y-auto space-y-6 flex-1">
            {/* Page Nav */}
            <div className="bg-gray-700/30 p-3 rounded border border-gray-600">
              <h3 className="text-gray-400 text-[10px] font-bold uppercase mb-2">
                1. Select Page
              </h3>
              <div className="flex gap-2">
                {pages.map((p, i) => (
                  <button
                    key={i}
                    onClick={() => setActivePageIdx(i)}
                    className={`h-10 w-10 rounded font-bold text-sm border-2 transition-all
                      ${
                        activePageIdx === i
                          ? "bg-yellow-500 text-black border-white scale-110"
                          : "bg-gray-700 border-transparent"
                      }
                      ${p.background ? "border-green-500" : ""} 
                    `}
                  >
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>

            {/* Backgrounds */}
            <div>
              <div className="flex justify-between mb-2">
                <h3 className="text-xs font-bold text-gray-400">
                  2. SELECT BACKGROUND
                </h3>
                <button
                  onClick={() => bgInput.current.click()}
                  className="text-[10px] bg-blue-600 px-2 py-1 rounded"
                >
                  + Upload
                </button>
                <input
                  type="file"
                  ref={bgInput}
                  hidden
                  onChange={(e) => handleUpload(e, "bg")}
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                {backgrounds.map((bg) => (
                  <img
                    key={bg.id}
                    src={bg.url}
                    onClick={() => updateActivePage({ background: bg })}
                    className={`h-16 w-full object-cover rounded border-2 cursor-pointer hover:border-white transition-all
                      ${
                        activePage.background?.id === bg.id
                          ? "border-yellow-500 opacity-100"
                          : "border-gray-600 opacity-50"
                      }`}
                  />
                ))}
              </div>
            </div>

            {/* PRIMARY CHARACTER */}
            <div className="bg-cyan-900/20 p-4 rounded border border-cyan-500/30">
              <h3 className="text-cyan-400 text-[10px] font-bold uppercase mb-2">
                3. PRIMARY CHARACTER (USER)
              </h3>

              <div className="grid grid-cols-3 gap-2">
                {userFaces.map((face) => (
                  <img
                    key={face.filename}
                    src={face.url}
                    onClick={() => {
                      setDesignUserId(face.user_id);
                      setUserFace(face);
                      addItem(face, "placeholder");
                    }}
                    className="w-full h-16 object-contain bg-gray-700 rounded cursor-pointer border border-gray-600 hover:border-white transition-all hover:scale-110"
                  />
                ))}
                {userFaces.length === 0 && (
                  <p className="text-[10px] text-gray-500 italic">
                    No user faces uploaded yet.
                  </p>
                )}
              </div>

              <div className="mb-2">
                <label className="text-[9px] text-cyan-200 block mb-1">
                  MOVEMENT (Select or Type Custom):
                </label>
                <select
                  value=""
                  onChange={(e) =>
                    updatePoseAndItems("primary", e.target.value)
                  }
                  className="w-full bg-gray-800 text-xs p-2 rounded-t border border-cyan-700 text-cyan-200 focus:outline-none mb-1"
                >
                  <option value="" disabled>
                    -- Quick Select --
                  </option>
                  <option>Standing Naturally</option>
                  <option>Sitting on Chair</option>
                  <option>Walking Forward</option>
                  <option>Running Fast</option>
                  <option>Fighting Stance</option>
                  <option>Holding a Weapon</option>
                </select>
                <input
                  type="text"
                  value={activePage.primaryPose}
                  onChange={(e) =>
                    updatePoseAndItems("primary", e.target.value)
                  }
                  placeholder="Or type custom action here..."
                  className="w-full bg-gray-900 text-white text-xs p-2 rounded-b border border-cyan-600 focus:border-white outline-none"
                />
              </div>
              {/* <button
                onClick={() => {
                  if (!userFace) {
                    alert("Please upload a face image first!");
                    return;
                  }
                  addItem(userFace, "placeholder");
                }}
                className="w-full py-3 bg-cyan-600 hover:bg-cyan-500 rounded text-white font-bold text-xs shadow-lg flex items-center justify-center gap-2 mt-2"
              >
                <span>👤</span> ADD USER HERO
              </button> */}
            </div>

            {/* SECONDARY CHARACTER */}
            <div className="bg-purple-900/20 p-4 rounded border border-purple-500/30">
              <div className="flex justify-between mb-2">
                <h3 className="text-purple-400 text-[10px] font-bold uppercase">
                  4. SECONDARY CHARACTER
                </h3>
                <button
                  onClick={() => {
                    if (!isUploadingCharacter) {
                      charInput.current.click();
                    }
                  }}
                  className="text-[9px] bg-purple-600 px-2 py-1 rounded text-white"
                >
                  {isUploadingCharacter ? "Processing..." : "+ Upload"}
                </button>
                <input
                  type="file"
                  ref={charInput}
                  hidden
                  onChange={(e) => handleUpload(e, "char")}
                />
              </div>
              <div className="mb-2">
                <label className="text-[9px] text-purple-200 block mb-1">
                  MOVEMENT (Select or Type Custom):
                </label>
                <select
                  value=""
                  onChange={(e) =>
                    updatePoseAndItems("secondary", e.target.value)
                  }
                  className="w-full bg-gray-800 text-xs p-2 rounded-t border border-purple-700 text-purple-200 focus:outline-none mb-1"
                >
                  <option value="" disabled>
                    -- Quick Select --
                  </option>
                  <option>Standing Menacingly</option>
                  <option>Sitting / Resting</option>
                  <option>Running / Charging</option>
                  <option>Flying / Hovering</option>
                  <option>Roaring / Howling</option>
                </select>
                <input
                  type="text"
                  value={activePage.secondaryPose}
                  onChange={(e) =>
                    updatePoseAndItems("secondary", e.target.value)
                  }
                  placeholder="Or type custom action here..."
                  className="w-full bg-gray-900 text-white text-xs p-2 rounded-b border border-purple-600 focus:border-white outline-none"
                />
              </div>
              <div className="grid grid-cols-4 gap-2 mt-2">
                {characters.map((char) => (
                  <img
                    key={char.id}
                    src={char.url}
                    onClick={() => addItem(char, "character")}
                    className="w-full h-16 object-contain bg-gray-700 rounded cursor-pointer border border-gray-600 hover:border-white transition-all hover:scale-110"
                  />
                ))}
                {characters.length === 0 && (
                  <p className="text-[10px] text-gray-500 italic">
                    No secondary chars yet.
                  </p>
                )}
              </div>
            </div>

            <textarea
              value={activePage.text}
              onChange={(e) => updateActivePage({ text: e.target.value })}
              className="w-full bg-black/30 p-2 text-xs text-white border border-gray-600 rounded resize-none"
              rows={3}
              placeholder="Story text..."
            />
            <button
              onClick={saveDesign}
              className="w-full mt-3 py-3 bg-green-600 hover:bg-green-500 rounded text-white font-bold text-xs shadow-lg"
            >
              SAVE DESIGN FOR USER
            </button>
          </div>
        ) : (
          <div className="p-8 flex flex-col items-center justify-center h-full space-y-6">
            <h2 className="text-3xl font-bold text-white">Create Your Story</h2>
            <div
              onClick={() => {
                if (!isUploadingFace) {
                  faceInput.current.click();
                }
              }}
              className="w-56 h-56 rounded-full border-4 border-dashed border-cyan-500 flex items-center justify-center cursor-pointer hover:bg-gray-800 overflow-hidden relative shadow-2xl"
            >
              {userFace ? (
                <img
                  src={userFace.url}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center">
                  {isUploadingFace ? (
                    <>
                      <span className="text-cyan-500 font-bold block text-sm">
                        Processing...
                      </span>
                      <span className="text-gray-400 text-[10px] font-bold">
                        Removing background
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="text-cyan-500 font-bold block text-2xl">
                        +
                      </span>
                      <span className="text-gray-400 text-xs font-bold">
                        UPLOAD FACE
                      </span>
                    </>
                  )}
                </div>
              )}
              <input
                type="file"
                ref={faceInput}
                hidden
                onChange={(e) => handleUpload(e, "face")}
              />
            </div>
            <button
              onClick={generateStory}
              disabled={isGenerating || !userFace || isUploadingFace}
              className={`w-full max-w-sm py-4 rounded-xl font-bold text-xl shadow-lg transition-all ${
                isGenerating
                  ? "bg-gray-600"
                  : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:scale-105"
              }`}
            >
              {isGenerating ? "GENERATING..." : "GENERATE PDF 🚀"}
            </button>
            {storyResult && (
              <a
                href={storyResult.pdf_url}
                target="_blank"
                className="bg-green-600 text-white px-8 py-4 rounded-xl font-bold hover:bg-green-500 shadow-lg"
              >
                DOWNLOAD PDF
              </a>
            )}
          </div>
        )}
        <button
          onClick={onLogout}
          className="py-2 px-4 rounded text-white font-bold text-xs mb-4"
        >
          LOGOUT
        </button>
      </div>

      {/* CANVAS */}
      <div className="flex-1 bg-black flex items-center justify-center bg-grid-pattern relative">
        {isAdmin ? (
          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            <div
              className="relative w-[800px] h-[600px] bg-gray-900 shadow-2xl border border-gray-700 overflow-hidden"
              style={{
                backgroundImage: activePage.background
                  ? `url(${activePage.background.url})`
                  : "none",
                backgroundSize: "cover",
                backgroundPosition: "center",
              }}
            >
              {!activePage.background && (
                <div className="absolute inset-0 flex items-center justify-center text-gray-600">
                  [Select a Background]
                </div>
              )}
              {activePage.items.map((item) => (
                <DraggableItem key={item.id} {...item} onRemove={removeItem} />
              ))}
            </div>
          </DndContext>
        ) : (
          <div className="w-[800px] h-[600px] bg-black shadow-2xl border border-gray-700" />
        )}
      </div>
    </div>
  );
}
