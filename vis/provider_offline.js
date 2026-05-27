// ==========================================
// provider_offline.js
// OFFLINE FILE PARSER & PLAYBACK CONTROLLER
// ==========================================

const OfflineProvider = {
    parsedData: null,
    uploadedFilePointer: null,
    currentLoadedChunkIndex: -1,
    headerLengthOffset: 0,
    chunkLoadPromise: null,
    chunkLoadIndexInFlight: -1,

    currentTime: 0, minTime: 0, maxTime: 0, timeMultiplier: 1,
    isPlaying: false, animationFrameId: null, lastFrameTime: 0, lastDynUpdate: 0,


    init: function() {
        document.getElementById("profileLoader")?.addEventListener("change", (e) => this.handleFileUpload(e));
        document.getElementById("btn-play")?.addEventListener("click", () => this.togglePlayback());
        document.getElementById("btn-step-back")?.addEventListener("click", () => this.stepToAdjacentEvent(-1));
        document.getElementById("btn-step-forward")?.addEventListener("click", () => this.stepToAdjacentEvent(1));

        document.getElementById("timeSlider")?.addEventListener("input", (e) => {
            document.getElementById("currentTimeLabel").textContent = parseFloat(e.target.value).toFixed(3);
        });

        document.getElementById("timeSlider")?.addEventListener("change", (e) => {
            this.pausePlayback();
            this.seekToTime(parseFloat(e.target.value));
        });

        const speedSlider = document.getElementById("speedSlider");
        if (speedSlider) {
            // Allow much slower playback
            speedSlider.min = "-6";
            speedSlider.max = "2";
            speedSlider.step = "0.1";

            speedSlider.addEventListener("input", () => this.updateSpeedLabel());
        }

        this.updateSpeedLabel();

        VisualiserCore.init("visCanvas");
    },

    decompressBlob: async function(blob) {
        const ds = new DecompressionStream('deflate');
        return await new Response(blob.stream().pipeThrough(ds)).text();
    },

    handleFileUpload: async function(event) {
        this.uploadedFilePointer = event.target.files[0];
        if (!this.uploadedFilePointer) return;

        try {
            const sizeBuf = await this.uploadedFilePointer.slice(0, 4).arrayBuffer();
            this.headerLengthOffset = 4 + new DataView(sizeBuf).getUint32(0, true);
            const headerText = await this.decompressBlob(this.uploadedFilePointer.slice(4, this.headerLengthOffset));
            
            this.parsedData = JSON.parse(headerText);
            
            window.parsedData = this.parsedData; 
            
            this.parsedData.timeline = [];
            this.currentLoadedChunkIndex = -1;
            
            this.initDashboard();
        } catch (error) {
            alert("Failed to parse the MPI profile data.");
            console.error(error);
        }
    }, 

    ensureValidTopology: function() {
	const metadata = this.parsedData.metadata || this.parsedData.info || {};

	if (!Array.isArray(this.parsedData.topology)) {
            this.parsedData.topology = [];
	}

	const topology = this.parsedData.topology;
	const totalRanks = Number(metadata.total_ranks || topology.length || 0);

	// If topology is completely missing, create a realistic fallback
	// This topology isn't the system map that can be provided, this is the 
	// information for the individual processes that should be collected at runtime.
	// Really we should fix this in the parser rather than faking it here.
	// TODO: Move to the parser.
	if (topology.length === 0 && totalRanks > 0) {
            for (let i = 0; i < totalRanks; i++) {
		topology.push({
                    rank: i,
                    hostname: "node-0",
                    chip: 0,
                    core: i
		});
            }
	}

	// Normalise records, but do NOT remap chip/core when a real blueprint exists.
	topology.forEach((rankObj, idx) => {
            if (!Number.isFinite(rankObj.rank)) rankObj.rank = idx;
            if (!Number.isFinite(rankObj.chip)) rankObj.chip = 0;
            if (!Number.isFinite(rankObj.core)) rankObj.core = 0;

            let host = (typeof rankObj.hostname === "string") ? rankObj.hostname.trim() : "";
            if (!host) host = `node-${idx}`;
            rankObj.hostname = host;
	});

	const bp = this.parsedData.hardware_blueprint;

	const hasFlatBlueprint =
            bp &&
            typeof bp === "object" &&
            !Array.isArray(bp) &&
            Object.keys(bp).some(k => k !== "metadata" && k !== "cabinets" && bp[k] && typeof bp[k] === "object");

	const hasCabinetBladeBlueprint =
            bp &&
            Array.isArray(bp.cabinets) &&
            bp.cabinets.some(c =>
			     Array.isArray(c.racks) &&
			     c.racks.some(r =>
					  Array.isArray(r.blades) &&
					  r.blades.some(b => Array.isArray(b.nodes) && b.nodes.length > 0)
					 )
			    );

	// If a usable blueprint already exists, KEEP IT.
	if (hasFlatBlueprint || hasCabinetBladeBlueprint) {
            console.log("Using provided hardware blueprint; topology inference skipped.");
            return;
	}

	// --------------------------------------------------
	// No usable blueprint present: infer a process layout
	// from the observed topology only.
	// --------------------------------------------------
	const hosts = new Map();

	topology.forEach((rankObj) => {
            const host = rankObj.hostname;
            const rawChip = Number.isFinite(rankObj.chip) ? rankObj.chip : 0;
            const rawCore = Number.isFinite(rankObj.core) ? rankObj.core : rankObj.rank;

            rankObj.raw_chip = rawChip;
            rankObj.raw_core = rawCore;

            if (!hosts.has(host)) {
		hosts.set(host, {
                    hostName: host,
                    ranks: [],
                    chipGroups: new Map(),
                    inferredCpuCount: 1,
                    inferredCoresPerCpu: 1
		});
            }

            const h = hosts.get(host);
            h.ranks.push(rankObj);

            if (!h.chipGroups.has(rawChip)) {
		h.chipGroups.set(rawChip, []);
            }
            h.chipGroups.get(rawChip).push(rankObj);
	});

	const hostList = Array.from(hosts.values()).sort((a, b) =>
							 a.hostName.localeCompare(b.hostName, undefined, { numeric: true, sensitivity: "base" })
							);

	hostList.forEach((hostObj) => {
            const chipEntries = Array.from(hostObj.chipGroups.entries()).sort((a, b) => a[0] - b[0]);
            let maxRanksOnAnyChip = 0;

            chipEntries.forEach(([rawChip, chipRanks], visualChipIdx) => {
		chipRanks.sort((a, b) => {
                    const ac = Number.isFinite(a.raw_core) ? a.raw_core : a.rank;
                    const bc = Number.isFinite(b.raw_core) ? b.raw_core : b.rank;
                    if (ac !== bc) return ac - bc;
                    return a.rank - b.rank;
		});

		chipRanks.forEach((rankObj, visualCoreIdx) => {
                    rankObj.chip = visualChipIdx;
                    rankObj.core = visualCoreIdx;
		});

		maxRanksOnAnyChip = Math.max(maxRanksOnAnyChip, chipRanks.length);
            });

            hostObj.inferredCpuCount = Math.max(1, chipEntries.length);
            hostObj.inferredCoresPerCpu = Math.max(1, maxRanksOnAnyChip);
	});

	const cols = Math.ceil(Math.sqrt(hostList.length || 1));
	const hostSpacing = 18;

	const flatBlueprint = {
            metadata: {
		system_name: metadata.system_name || "Inferred Process Topology"
            }
	};

	hostList.forEach((hostObj, index) => {
            const col = index % cols;
            const row = Math.floor(index / cols);

            flatBlueprint[hostObj.hostName] = {
		x: (col - (cols - 1) / 2) * hostSpacing,
		y: 0,
		z: (row - (Math.ceil(hostList.length / cols) - 1) / 2) * hostSpacing,
		cpus: hostObj.inferredCpuCount,
		cores_per_cpu: hostObj.inferredCoresPerCpu
            };
	});

	this.parsedData.hardware_blueprint = flatBlueprint;

	console.log("Inferred topology:");
	hostList.forEach(h => {
            console.log(
		h.hostName,
		`chips=${h.inferredCpuCount}`,
		`max-ranks-per-chip=${h.inferredCoresPerCpu}`
            );
	});
    },


    initDashboard: function() {
        this.pausePlayback();
        VisualiserCore.clearTopology();

        const chunks = this.parsedData.chunks;
        this.minTime = (chunks && chunks.length > 0) ? chunks[0].t_start : 0;
        this.maxTime = (chunks && chunks.length > 0) ? chunks[chunks.length - 1].t_end : 0;
        this.timeMultiplier = (this.maxTime - this.minTime > 0) ? (this.maxTime - this.minTime) / 10.0 : 1;

        const slider = document.getElementById("timeSlider");
        if (slider) { slider.step = "any"; slider.min = this.minTime; slider.max = this.maxTime; slider.disabled = false; }
        if (document.getElementById("btn-play")) document.getElementById("btn-play").disabled = false;

	this.ensureValidTopology();

        // Hand the blueprint off to the core
        VisualiserCore.buildTopology(this.parsedData.hardware_blueprint, this.parsedData.topology, this.parsedData.metadata || this.parsedData.info);
        VisualiserCore.initSpectrograms(this.parsedData.statistics);

        if (window.AnalyticsUI) {
            AnalyticsUI.renderAnalytics(window.parsedData);
        }
        if (window.Analytics3D) {
            Analytics3D.setAnalysis(window.parsedData.analysis);
            Analytics3D.refreshHighlights();
        }

        this.seekToTime(this.minTime).catch(err => { console.error(err); this.pausePlayback(); });
    },


    ensureChunkLoadedForTime: async function(time) {
        if (!this.parsedData?.chunks || !this.uploadedFilePointer) return;
        const chunks = this.parsedData.chunks;

        while (true) {
            let targetIndex = chunks.findIndex(c => time <= c.t_end);
            if (targetIndex === -1) targetIndex = chunks.length - 1;

            const requiredKey = `${Math.max(0, targetIndex - 1)}:${targetIndex}`;
            if (this.currentLoadedChunkIndex === requiredKey) return;

            if (this.chunkLoadPromise) {
                if (this.chunkLoadIndexInFlight === requiredKey) {
                    await this.chunkLoadPromise;
                    return;
                }
                await this.chunkLoadPromise;
                continue;
            }

            this.chunkLoadIndexInFlight = requiredKey;
            const overlay = document.getElementById("loadingOverlay");
            const loadingText = document.getElementById("loadingText");

            this.chunkLoadPromise = (async () => {
                try {
                    if (overlay) overlay.style.display = "block";
                    if (loadingText) loadingText.textContent = `Unpacking Chunk ${targetIndex + 1}...`;
                    await new Promise(r => setTimeout(r, 0));

                    const indices = [];
                    if (targetIndex > 0) indices.push(targetIndex - 1);
                    indices.push(targetIndex);

                    let mergedTimeline = [];

                    for (const idx of indices) {
                        const c = chunks[idx];
                        const blob = this.uploadedFilePointer.slice(
                            this.headerLengthOffset + c.offset,
                            this.headerLengthOffset + c.offset + c.size
                        );
                        const chunkTimeline = JSON.parse(await this.decompressBlob(blob));
                        mergedTimeline = mergedTimeline.concat(chunkTimeline);
                    }

                    if (mergedTimeline.length > 1) {
                        mergedTimeline.sort((a, b) => a.time - b.time);
                    }

                    this.parsedData.timeline = mergedTimeline;
                    this.currentLoadedChunkIndex = requiredKey;
                } finally {
                    if (overlay) overlay.style.display = "none";
                }
            })();

            await this.chunkLoadPromise;
            this.chunkLoadPromise = null;
            this.chunkLoadIndexInFlight = -1;
            return;
        }
    },

    seekToTime: async function(time) {
        this.currentTime = time;
        if (document.getElementById("timeSlider")) document.getElementById("timeSlider").value = this.currentTime;
        if (document.getElementById("currentTimeLabel")) document.getElementById("currentTimeLabel").textContent = this.currentTime.toFixed(3);
        
        if (window.AnalyticsUI) {
            AnalyticsUI.updateAnalyticsTimeWindowIndicator(this.currentTime);
        }
        
        await this.ensureChunkLoadedForTime(this.currentTime);
        const activeEvents = this.getActiveEventsForWindow();
	
        VisualiserCore.clearGlow();
	
        VisualiserCore.renderFrame(activeEvents);
        VisualiserCore.updateDynamicSpectrogram(activeEvents, this.parsedData.statistics);
    },

    getActiveEventsForWindow: function() {
        const speed = this.getSpeedMultiplier();

        const winSize = Math.min(0.2, Math.max(1e-9, 0.05 * speed));
        const minWin = this.currentTime - winSize;
        const minCollWin = this.currentTime - Math.max(winSize * 8.0, 0.5);

        const timeline = this.parsedData.timeline;
        const activeEvents = [];
        if (!timeline || timeline.length === 0) return activeEvents;

        let l = 0, r = timeline.length - 1, m = 0;
        while (l <= r) {
            m = Math.floor((l + r) / 2);
            if (timeline[m].time <= this.currentTime) l = m + 1;
            else r = m - 1;
        }

        let captured = 0;
        for (let i = r; i >= 0; i--) {
            const ev = timeline[i];
            const evTime = ev.time;
            const callType = ev.call || ev.message_type;
            const cat = window.VisualiserCore ? window.VisualiserCore.MPI_CATEGORIES[callType] : null || { type: "unknown" };
            const isColl = (cat.type === "collective" || cat.type === "lifecycle");

            if (evTime >= minCollWin) {
                if (evTime >= minWin || isColl) {
                    activeEvents.push(ev);
                    if (++captured >= 800) break;
                }
            } else {
                break;
            }
        }

        return activeEvents.reverse();
    },


    getSpeedRaw: function() {
        return parseFloat(document.getElementById("speedSlider")?.value || "0");
    },

    getSpeedMultiplier: function() {
        return Math.pow(10, this.getSpeedRaw());
    },

    formatSpeedMultiplier: function(mult) {
        if (!Number.isFinite(mult) || mult <= 0) return "0x";
        if (mult >= 0.01 && mult < 1000) return `${mult.toFixed(3)}x`;
        return `${mult.toExponential(2)}x`;
    },

    updateSpeedLabel: function() {
        const speedLabel = document.getElementById("speedLabel");
        if (speedLabel) {
            speedLabel.textContent = this.formatSpeedMultiplier(this.getSpeedMultiplier());
        }
    },

    findFirstEventAfter: function(timeline, time) {
        let l = 0, r = timeline.length - 1;
        let ans = -1;

        while (l <= r) {
            const m = (l + r) >> 1;
            if (timeline[m].time > time) {
                ans = m;
                r = m - 1;
            } else {
                l = m + 1;
            }
        }

        return ans;
    },

    findLastEventBefore: function(timeline, time) {
        let l = 0, r = timeline.length - 1;
        let ans = -1;

        while (l <= r) {
            const m = (l + r) >> 1;
            if (timeline[m].time < time) {
                ans = m;
                l = m + 1;
            } else {
                r = m - 1;
            }
        }

        return ans;
    },

    stepToAdjacentEvent: async function(direction) {
        this.pausePlayback();

        if (!this.parsedData?.chunks || !this.uploadedFilePointer) return;

        const chunks = this.parsedData.chunks;
        const EPS = 1e-12;

        await this.ensureChunkLoadedForTime(this.currentTime);

        let timeline = this.parsedData.timeline || [];
        let idx = (direction > 0)
            ? this.findFirstEventAfter(timeline, this.currentTime + EPS)
            : this.findLastEventBefore(timeline, this.currentTime - EPS);

        if (idx !== -1) {
            await this.seekToTime(timeline[idx].time);
            return;
        }

        let chunkIndex = chunks.findIndex(c => this.currentTime <= c.t_end);
        if (chunkIndex === -1) chunkIndex = chunks.length - 1;

        const neighbourIndex = (direction > 0)
            ? Math.min(chunks.length - 1, chunkIndex + 1)
            : Math.max(0, chunkIndex - 1);

        if (neighbourIndex !== chunkIndex) {
            const probeTime = (direction > 0)
                ? chunks[neighbourIndex].t_start
                : chunks[neighbourIndex].t_end;

            await this.ensureChunkLoadedForTime(probeTime);

            timeline = this.parsedData.timeline || [];
            idx = (direction > 0)
                ? this.findFirstEventAfter(timeline, this.currentTime + EPS)
                : this.findLastEventBefore(timeline, this.currentTime - EPS);

            if (idx !== -1) {
                await this.seekToTime(timeline[idx].time);
                return;
            }
        }

        await this.seekToTime(direction > 0 ? this.maxTime : this.minTime);
    },


    togglePlayback: function() {
        this.isPlaying = !this.isPlaying;
        VisualiserCore.isDecayEnabled = this.isPlaying;
        const btn = document.getElementById("btn-play");
        if (btn) btn.innerHTML = this.isPlaying ? "<b>|| Pause</b>" : "<b>▶ Play</b>";
        if (this.isPlaying) { this.lastFrameTime = performance.now(); this.playLoop(performance.now()); }
        else cancelAnimationFrame(this.animationFrameId);
    },

    pausePlayback: function() {
        this.isPlaying = false;
        VisualiserCore.isDecayEnabled = false;
        const btn = document.getElementById("btn-play");
        if (btn) btn.innerHTML = "<b>▶ Play</b>";
        cancelAnimationFrame(this.animationFrameId);
    },

    playLoop: async function(timestamp) {
        if (!this.isPlaying) return;
        const dt = Math.min((timestamp - this.lastFrameTime) / 1000, 0.05);
        this.lastFrameTime = timestamp;
       
        const speed = this.getSpeedMultiplier();
        let nextTime = this.currentTime + (dt * this.timeMultiplier * speed);

        if (nextTime >= this.maxTime) { await this.seekToTime(this.maxTime); this.pausePlayback(); return; }

        this.currentTime = nextTime;
        if (document.getElementById("timeSlider")) document.getElementById("timeSlider").value = this.currentTime;
        if (document.getElementById("currentTimeLabel")) document.getElementById("currentTimeLabel").textContent = this.currentTime.toFixed(3);

        if (window.AnalyticsUI) {
            AnalyticsUI.updateAnalyticsTimeWindowIndicator(this.currentTime);
        }

        await this.ensureChunkLoadedForTime(this.currentTime);
        const activeEvents = this.getActiveEventsForWindow();
        
        VisualiserCore.renderFrame(activeEvents);
        if (timestamp - this.lastDynUpdate > 100) { VisualiserCore.updateDynamicSpectrogram(activeEvents, this.parsedData.statistics); this.lastDynUpdate = timestamp; }

        if (this.isPlaying) this.animationFrameId = requestAnimationFrame((ts) => this.playLoop(ts));
    }
};

document.addEventListener("DOMContentLoaded", () => OfflineProvider.init());
