// Global State
let parsedData = null;
let simulation = null;
let nodeMap = new Map(); // Maps rank -> D3 node object
let svg, gContainer;

// Playback State
let isPlaying = false;
let currentTime = 0;
let maxTime = 0;
let animationFrameId = null;

// The amount of time a message stays visible on screen (adjust based on your dataset)
const TIME_WINDOW = 0.05; 

document.addEventListener("DOMContentLoaded", () => {
    // 1. Setup SVG and Zoom/Pan
    svg = d3.select("#visCanvas");
    gContainer = svg.append("g"); // Everything goes inside here so it scales together

    const zoom = d3.zoom()
        .scaleExtent([0.1, 10])
        .on("zoom", (event) => {
            gContainer.attr("transform", event.transform);
        });
    svg.call(zoom);

    // 2. Setup Event Listeners
    document.getElementById("profileLoader").addEventListener("change", handleFileUpload);
    document.getElementById("timeSlider").addEventListener("input", handleManualSeek);
    document.getElementById("btn-play").addEventListener("click", togglePlayback);
});

// --- Data Loading ---
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            parsedData = JSON.parse(e.target.result);
            initDashboard();
        } catch (error) {
            alert("Error parsing JSON file. Is it a valid .mpic_parsed profile?");
            console.error(error);
        }
    };
    reader.readAsText(file);
}

function initDashboard() {
    // Reset state
    pausePlayback();
    gContainer.selectAll("*").remove();
    nodeMap.clear();

    const timeline = parsedData.timeline;
    const topology = parsedData.topology;

    // Update Stats UI
    maxTime = timeline.length > 0 ? timeline[timeline.length - 1].time : 0;
    document.getElementById("stat-ranks").textContent = topology.length;
    document.getElementById("stat-events").textContent = timeline.length;
    document.getElementById("stat-duration").textContent = maxTime.toFixed(3);
    
    // Enable Controls
    const slider = document.getElementById("timeSlider");
    slider.max = maxTime;
    slider.disabled = false;
    document.getElementById("btn-play").disabled = false;

    buildNetworkTopology(topology);
    seekToTime(0);
}

// --- Topology & Physics ---
function buildNetworkTopology(nodesData) {
    const width = document.getElementById("canvas-container").clientWidth;
    const height = document.getElementById("canvas-container").clientHeight;

    // We create a force simulation just for the nodes to spread them out beautifully
    simulation = d3.forceSimulation(nodesData)
        .force("charge", d3.forceManyBody().strength(-400)) // Repel each other
        .force("center", d3.forceCenter(width / 2, height / 2)) // Pull to center
        .force("collide", d3.forceCollide().radius(30)); // Don't overlap

    // Draw the Links Group (Behind nodes)
    gContainer.append("g").attr("class", "links-layer");

    // Draw the Nodes Group
    const nodeGroup = gContainer.append("g")
        .selectAll("g")
        .data(nodesData)
        .enter().append("g")
        .call(d3.drag() // Allow user to drag nodes manually
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Draw circles for nodes
    nodeGroup.append("circle")
        .attr("class", "node")
        .attr("r", 15)
        .on("mouseenter", (e, d) => showInspector(`Rank: ${d.rank}<br>Hostname: ${d.hostname}<br>PID: ${d.pid}<br>Core/Chip: ${d.core}/${d.chip}`))
        .on("mouseleave", () => showInspector("Hover over a node or active communication link to see details."));

    // Draw Rank ID labels inside circles
    nodeGroup.append("text")
        .attr("class", "node-label")
        .text(d => d.rank);

    // Map the simulated nodes to our map so the links can find their X/Y coords fast
    nodesData.forEach(n => nodeMap.set(n.rank, n));

    // Update positions on every physics tick
    simulation.on("tick", () => {
        nodeGroup.attr("transform", d => `translate(${d.x},${d.y})`);
        // If physics is running while timeline is playing, update link positions too
        updateActiveLinksPosition();
    });
}

// --- Timeline & Animation ---
function handleManualSeek(event) {
    pausePlayback();
    seekToTime(parseFloat(event.target.value));
}

function seekToTime(time) {
    currentTime = time;
    document.getElementById("timeSlider").value = currentTime;
    document.getElementById("currentTimeLabel").textContent = currentTime.toFixed(3);
    renderActiveCommunications();
}

function renderActiveCommunications() {
    if (!parsedData || !parsedData.timeline) return;

    // Find messages that happen within our current TIME_WINDOW
    const activeEvents = parsedData.timeline.filter(d => 
        d.time <= currentTime && d.time >= (currentTime - TIME_WINDOW)
        // Skip self-communications (like Waits/Barriers) for the graph drawing
        && d.sender !== d.receiver 
    );

    const linksLayer = gContainer.select(".links-layer");
    
    // Bind data to lines based on unique event_id
    const linkSelection = linksLayer.selectAll("line")
        .data(activeEvents, d => d.event_id + "-" + d.category);

    // ENTER: New messages arriving in the window
    linkSelection.enter().append("line")
        .attr("class", "link")
        .attr("stroke-width", d => Math.max(2, Math.min(10, d.bytes / 1024))) // Scale thickness based on bytes (2px to 10px)
        .on("mouseenter", (e, d) => showInspector(`<b>${d.call}</b><br>From: Rank ${d.sender}<br>To: Rank ${d.receiver}<br>Bytes: ${d.bytes}<br>Time: ${d.time.toFixed(4)}s`))
        .on("mouseleave", () => showInspector("Hover over a node or active communication link to see details."))
        .merge(linkSelection) // UPDATE: Existing messages
        .attr("x1", d => nodeMap.has(d.sender) ? nodeMap.get(d.sender).x : 0)
        .attr("y1", d => nodeMap.has(d.sender) ? nodeMap.get(d.sender).y : 0)
        .attr("x2", d => nodeMap.has(d.receiver) ? nodeMap.get(d.receiver).x : 0)
        .attr("y2", d => nodeMap.has(d.receiver) ? nodeMap.get(d.receiver).y : 0);

    // EXIT: Messages falling out of the time window
    linkSelection.exit().remove();
}

function updateActiveLinksPosition() {
    gContainer.select(".links-layer").selectAll("line")
        .attr("x1", d => nodeMap.has(d.sender) ? nodeMap.get(d.sender).x : 0)
        .attr("y1", d => nodeMap.has(d.sender) ? nodeMap.get(d.sender).y : 0)
        .attr("x2", d => nodeMap.has(d.receiver) ? nodeMap.get(d.receiver).x : 0)
        .attr("y2", d => nodeMap.has(d.receiver) ? nodeMap.get(d.receiver).y : 0);
}

// --- Playback Loop ---
function togglePlayback() {
    if (isPlaying) {
        pausePlayback();
    } else {
        isPlaying = true;
        document.getElementById("btn-play").innerHTML = "⏸ Pause";
        lastFrameTime = performance.now();
        animationFrameId = requestAnimationFrame(playLoop);
    }
}

function pausePlayback() {
    isPlaying = false;
    document.getElementById("btn-play").innerHTML = "▶ Play";
    if (animationFrameId) cancelAnimationFrame(animationFrameId);
}

let lastFrameTime = 0;
function playLoop(timestamp) {
    if (!isPlaying) return;

    // Calculate delta time
    const deltaTime = (timestamp - lastFrameTime) / 1000; // in seconds
    lastFrameTime = timestamp;

    const speed = parseFloat(document.getElementById("speedSlider").value);
    
    // Increment time based on real delta time * multiplier
    let nextTime = currentTime + (deltaTime * speed);

    if (nextTime >= maxTime) {
        seekToTime(maxTime);
        pausePlayback();
        return;
    }

    seekToTime(nextTime);
    animationFrameId = requestAnimationFrame(playLoop);
}

// --- Utility Functions ---
function showInspector(htmlContent) {
    document.getElementById("inspector-content").innerHTML = htmlContent;
}

// Physics drag behaviors
function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x; d.fy = d.y;
}
function dragged(event, d) {
    d.fx = event.x; d.fy = event.y;
}
function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null; d.fy = null;
}
