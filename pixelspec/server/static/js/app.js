/**
 * PixelSpec Web UI Frontend Logic
 * Real-time inspection controller, intermediate stage viewer, and report exporter.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const fileInfo = document.getElementById("file-info");
  const fileName = document.getElementById("file-name");
  const fileMeta = document.getElementById("file-meta");
  const btnRemoveFile = document.getElementById("btn-remove-file");
  const btnInspect = document.getElementById("btn-inspect");
  const profileSelect = document.getElementById("profile-select");
  const profileDesc = document.getElementById("profile-desc");
  const emptyState = document.getElementById("empty-state");
  const resultsPanel = document.getElementById("results-panel");
  const stageTabs = document.getElementById("stage-tabs");
  const activeStageImg = document.getElementById("active-stage-img");
  const stageCaption = document.getElementById("stage-caption");
  const btnExportHtml = document.getElementById("btn-export-html");
  const segButtons = document.querySelectorAll(".seg-btn");
  const comparisonBanner = document.getElementById("comparison-banner");

  let selectedFile = null;
  let currentInspectionMode = "advanced";
  let activeInspectionData = null;

  const PROFILE_DESCRIPTIONS = {
    standard: "Standard general catalog inspection suitable for mainstream e-commerce listings.",
    studio_pro: "Strict guidelines requiring pure seamless background (RGB > 245) and high sharpness.",
    relaxed: "Accommodating profile for secondary lifestyle shots or vendor uploads."
  };

  profileSelect.addEventListener("change", (e) => {
    profileDesc.textContent = PROFILE_DESCRIPTIONS[e.target.value] || "";
  });

  // Pipeline mode toggles
  segButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      segButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentInspectionMode = btn.getAttribute("data-mode");
    });
  });

  // Drag and drop handlers
  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  btnRemoveFile.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.style.display = "none";
    dropZone.style.display = "block";
    btnInspect.disabled = true;
    resultsPanel.style.display = "none";
    emptyState.style.display = "block";
  });

  function handleFileSelected(file) {
    if (!file.type.match("image/(jpeg|png)")) {
      alert("Please upload a valid JPEG or PNG image.");
      return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileMeta.textContent = (file.size / (1024 * 1024)).toFixed(2) + " MB";
    dropZone.style.display = "none";
    fileInfo.style.display = "flex";
    btnInspect.disabled = false;
  }

  // Run Inspection
  btnInspect.addEventListener("click", async () => {
    if (!selectedFile) return;

    btnInspect.disabled = true;
    btnInspect.querySelector(".btn-spinner").style.display = "inline-block";
    btnInspect.querySelector(".btn-label").textContent = "Inspecting...";

    const formData = new FormData();
    formData.append("file", selectedFile);

    const profileKey = profileSelect.value;
    const url = `/api/inspect?profile=${profileKey}&mode=${currentInspectionMode}`;

    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || "Inspection request failed.");
      }

      const data = await response.json();
      activeInspectionData = data;
      renderResults(data);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      btnInspect.disabled = false;
      btnInspect.querySelector(".btn-spinner").style.display = "none";
      btnInspect.querySelector(".btn-label").textContent = "Run Inspection";
    }
  });

  // Render Inspection Results
  function renderResults(data) {
    emptyState.style.display = "none";
    resultsPanel.style.display = "block";

    let primaryData = data;
    if (currentInspectionMode === "comparison") {
      comparisonBanner.style.display = "block";
      renderComparisonBanner(data.summary);
      primaryData = data.advanced_full;
    } else {
      comparisonBanner.style.display = "none";
    }

    // Verdict and score
    const verdictBadge = document.getElementById("verdict-badge");
    const overallScore = document.getElementById("overall-score");
    const resPipelineName = document.getElementById("res-pipeline-name");
    const resLatency = document.getElementById("res-latency");

    const verdict = primaryData.verdict || "UNKNOWN";
    verdictBadge.textContent = verdict;
    verdictBadge.className = "verdict-badge " + (verdict === "PASS" ? "pass" : (verdict === "NEEDS_IMPROVEMENT" ? "warning" : "fail"));

    overallScore.textContent = primaryData.overall_score || "0";
    resPipelineName.textContent = primaryData.pipeline_name || "DIP Pipeline";
    resLatency.textContent = primaryData.elapsed_ms || "0";

    // Recommendations
    const recsList = document.getElementById("recs-list");
    recsList.innerHTML = "";
    const recs = primaryData.recommendations || [];
    if (recs.length === 0) {
      const li = document.createElement("li");
      li.textContent = "Photograph satisfies all current compliance checks.";
      recsList.appendChild(li);
    } else {
      recs.forEach(r => {
        const li = document.createElement("li");
        li.textContent = r;
        recsList.appendChild(li);
      });
    }

    // Metrics Breakdown
    const m = primaryData.metrics || {};
    
    // Sharpness
    const sharp = m.sharpness || {};
    document.getElementById("m-sharp-score").textContent = (sharp.sharpness_score || 0) + "%";
    document.getElementById("bar-sharp").style.width = (sharp.sharpness_score || 0) + "%";
    document.getElementById("m-tenengrad").textContent = sharp.tenengrad_gradient || "--";
    document.getElementById("m-lap-var").textContent = sharp.laplacian_variance || "--";
    document.getElementById("m-fft-ratio").textContent = sharp.fft_high_freq_ratio || "--";

    // Exposure
    const exp = m.exposure || {};
    document.getElementById("m-exp-score").textContent = (exp.exposure_score || 0) + "%";
    document.getElementById("bar-exp").style.width = (exp.exposure_score || 0) + "%";
    document.getElementById("m-highlight-clip").textContent = ((exp.highlight_clipping_ratio || 0) * 100).toFixed(1) + "%";
    document.getElementById("m-shadow-clip").textContent = ((exp.shadow_clipping_ratio || 0) * 100).toFixed(1) + "%";
    document.getElementById("m-entropy").textContent = exp.shannon_entropy || "--";

    // Background
    const bg = m.background || {};
    document.getElementById("m-bg-score").textContent = (bg.purity_score || 0) + "%";
    document.getElementById("bar-bg").style.width = (bg.purity_score || 0) + "%";
    document.getElementById("m-delta-e").textContent = bg.median_delta_e || "--";
    document.getElementById("m-dispersion").textContent = bg.dispersion_std || "--";
    document.getElementById("m-pure-white").textContent = bg.is_pure_white ? "Yes (Studio)" : "No";

    // Framing
    const frame = m.framing || {};
    document.getElementById("m-frame-score").textContent = (frame.framing_score || 0) + "%";
    document.getElementById("bar-frame").style.width = (frame.framing_score || 0) + "%";
    document.getElementById("m-occupancy").textContent = ((frame.linear_coverage || 0) * 100).toFixed(1) + "%";
    document.getElementById("m-center-offset").textContent = ((frame.center_offset || 0) * 100).toFixed(1) + "%";
    document.getElementById("m-edge-clipped").textContent = frame.is_edge_clipped ? "Yes (Clipping Defect!)" : "None";

    // Noise
    const noise = m.noise || {};
    document.getElementById("m-noise-score").textContent = (noise.noise_score || 0) + "%";
    document.getElementById("bar-noise").style.width = (noise.noise_score || 0) + "%";
    document.getElementById("m-mad-sigma").textContent = noise.estimated_noise_sigma || "--";
    document.getElementById("m-snr").textContent = (noise.snr_db || "--") + " dB";
    document.getElementById("m-noise-verdict").textContent = noise.verdict || "--";

    // Setup Intermediate Stages Tabs
    setupStageViewer(primaryData.stage_images || {});
  }

  function renderComparisonBanner(summary) {
    if (!summary) return;
    const b = summary.baseline;
    const a = summary.advanced;

    document.getElementById("comp-base-score").textContent = b.score + " / 100";
    document.getElementById("comp-base-verdict").textContent = b.verdict;
    document.getElementById("comp-base-time").textContent = b.elapsed_ms + " ms";
    document.getElementById("comp-base-defects").textContent = b.defect_count;

    document.getElementById("comp-adv-score").textContent = a.score + " / 100";
    document.getElementById("comp-adv-verdict").textContent = a.verdict;
    document.getElementById("comp-adv-time").textContent = a.elapsed_ms + " ms";
    document.getElementById("comp-adv-defects").textContent = a.defect_count;
  }

  const STAGE_LABELS = {
    annotated: { label: "Final Overlay", desc: "Annotated image showing product bounding box, center alignment, and margin guides." },
    refined_mask: { label: "GrabCut Mask", desc: "Binary product segmentation mask refined via graph cuts and contour hole filling." },
    delta_e_map: { label: "CIELAB Delta E", desc: "Per-pixel color distance map from estimated border background." },
    edge_heatmap: { label: "Sharpness Gradient", desc: "Spatial Sobel & Laplacian gradient intensity heatmap." },
    fft_spectrum: { label: "2D FFT Spectrum", desc: "Log-scale magnitude spectrum revealing high-frequency detail distribution." },
    noise_residual_map: { label: "Noise Residuals", desc: "High-frequency pseudo-Laplacian residual map used for MAD sigma estimation." },
    bilateral_filter: { label: "Bilateral Filter", desc: "Edge-preserving smoothed representation used prior to color segmentation." },
    otsu_raw: { label: "Otsu Raw Mask", desc: "Classical global thresholding response." }
  };

  function setupStageViewer(stageImages) {
    stageTabs.innerHTML = "";
    const stageKeys = Object.keys(stageImages);
    if (stageKeys.length === 0) return;

    // Put 'annotated' first if present
    const sortedKeys = stageKeys.sort((a, b) => (a === "annotated" ? -1 : (b === "annotated" ? 1 : 0)));

    sortedKeys.forEach((key, index) => {
      const btn = document.createElement("button");
      btn.className = "tab-btn" + (index === 0 ? " active" : "");
      btn.textContent = STAGE_LABELS[key]?.label || key;
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        activeStageImg.src = stageImages[key];
        stageCaption.textContent = STAGE_LABELS[key]?.desc || key;
      });
      stageTabs.appendChild(btn);
    });

    // Display first tab
    const firstKey = sortedKeys[0];
    activeStageImg.src = stageImages[firstKey];
    stageCaption.textContent = STAGE_LABELS[firstKey]?.desc || firstKey;
  }

  // Export HTML Report
  btnExportHtml.addEventListener("click", async () => {
    if (!activeInspectionData) return;
    const targetData = activeInspectionData.advanced_full || activeInspectionData;

    try {
      const response = await fetch("/api/export-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(targetData)
      });
      const htmlText = await response.text();
      const reportWindow = window.open("", "_blank");
      reportWindow.document.write(htmlText);
      reportWindow.document.close();
    } catch (e) {
      alert("Failed to export report: " + e.message);
    }
  });

});
