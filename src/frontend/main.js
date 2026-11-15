"use strict";

const columns = {
    people: { x: 34, width: 260, title: "PEOPLE", count: 5 },
    orgs: { x: 355, width: 310, title: "ORGANIZATIONS", count: 6 },
    events: { x: 726, width: 360, title: "EVENTS & SERIES", count: 9 },
    tags: { x: 1147, width: 250, title: "TOPICS", count: 5 },
};

const nodes = [
    { id: "avery", type: "people", x: 34, y: 635, title: "Avery", subtitle: "Chapter admin", icon: "A", description: "Admin of the Sigma Chi Pi Chapter. Avery publishes chapter events and confirmed Drew's membership." },
    { id: "blake", type: "people", x: 34, y: 360, title: "Blake", subtitle: "National admin", icon: "B", description: "Admin of Alpha Beta National, and accepted its co-host invitation for the philanthropy 5K." },
    { id: "casey", type: "people", x: 34, y: 485, title: "Casey", subtitle: "Club admin", icon: "C", description: "Admin of the Robotics Club. Casey published Robot demo day and tagged the club and event with Robotics." },
    { id: "drew", type: "people", x: 34, y: 775, title: "Drew", subtitle: "Chapter officer", icon: "D", description: "Confirmed chapter member with the Officer role at Sigma Chi Pi Chapter." },
    { id: "emery", type: "people", x: 34, y: 525, title: "Emery", subtitle: "Student · request pending", icon: "E", badge: "PENDING", badgeTone: "warning", description: "Emery has requested membership in Robotics Club. The request has not been confirmed yet." },

    { id: "university", type: "orgs", x: 355, y: 135, title: "Northbridge University", subtitle: "Institution", icon: "U", description: "The university sits above the Interfraternity Council and Robotics Club in the demo hierarchy." },
    { id: "national", type: "orgs", x: 355, y: 340, title: "Alpha Beta National", subtitle: "National organization", icon: "N", description: "The national organization has its own admin, Blake, and co-hosts the Spring philanthropy 5K." },
    { id: "ifc", type: "orgs", x: 355, y: 555, title: "Northbridge Interfraternity Council", subtitle: "Council", icon: "C", description: "The Interfraternity Council is under Northbridge University and includes the Sigma Chi Pi Chapter in its hierarchy." },
    { id: "chapter", type: "orgs", x: 355, y: 765, title: "Sigma Chi Pi Chapter", subtitle: "Chapter · claimed", icon: "Σ", badge: "CLAIMED", description: "The chapter is part of Alpha Beta National and the Interfraternity Council. Avery is its admin; Drew is a confirmed officer. It owns the weekly meeting series and chapter events." },
    { id: "robotics", type: "orgs", x: 355, y: 470, title: "Robotics Club", subtitle: "Club · claimed", icon: "R", badge: "CLAIMED", description: "The club is under Northbridge University. Casey is its admin; Emery's membership request is pending. The club hosts Robot demo day." },
    { id: "chess", type: "orgs", x: 355, y: 960, title: "Chess Club", subtitle: "Club · unclaimed", icon: "♟", badge: "UNCLAIMED", badgeTone: "muted", description: "A deliberately unclaimed organization listing. It has no admin or hierarchy relationships in the demo data." },

    { id: "series", type: "events", x: 726, y: 65, title: "Weekly chapter meeting", subtitle: "Recurring series · weekly", icon: "↻", description: "A weekly event series owned by the Sigma Chi Pi Chapter, with four upcoming meeting occurrences." },
    { id: "meeting1", type: "events", x: 726, y: 180, title: "Chapter meeting · 1", subtitle: "Occurrence · Student Center", icon: "◷", description: "First of four upcoming occurrences in the Weekly chapter meeting series. Location: Student Center, Room 204." },
    { id: "meeting2", type: "events", x: 726, y: 285, title: "Chapter meeting · 2", subtitle: "Occurrence · Student Center", icon: "◷", description: "Second of four upcoming occurrences in the Weekly chapter meeting series. Location: Student Center, Room 204." },
    { id: "meeting3", type: "events", x: 726, y: 390, title: "Chapter meeting · 3", subtitle: "Occurrence · Student Center", icon: "◷", description: "Third of four upcoming occurrences in the Weekly chapter meeting series. Location: Student Center, Room 204." },
    { id: "meeting4", type: "events", x: 726, y: 495, title: "Chapter meeting · 4", subtitle: "Occurrence · Student Center", icon: "◷", description: "Fourth of four upcoming occurrences in the Weekly chapter meeting series. Location: Student Center, Room 204." },
    { id: "fundraiser", type: "events", x: 726, y: 610, title: "Spring philanthropy 5K", subtitle: "Published · North Field", icon: "✳", description: "A published chapter fundraiser at North Field, co-hosted by Alpha Beta National. Tagged Philanthropy." },
    { id: "demo", type: "events", x: 726, y: 725, title: "Robot demo day", subtitle: "Published · Engineering Hall", icon: "⚙", description: "A published Robotics Club event at Engineering Hall, capacity 60. Tagged Robotics." },
    { id: "mixer", type: "events", x: 726, y: 840, title: "Fall mixer", subtitle: "Cancelled", icon: "×", badge: "CANCELLED", badgeTone: "warning", description: "A chapter event that was cancelled. The graph keeps it to illustrate an event lifecycle state." },
    { id: "formal", type: "events", x: 726, y: 955, title: "Formal", subtitle: "Draft · not published", icon: "✎", badge: "DRAFT", badgeTone: "muted", description: "A chapter event still in draft. It is included to show that not every event in the graph is publicly discoverable." },

    { id: "philanthropy", type: "tags", x: 1147, y: 260, title: "Philanthropy", subtitle: "Topic", icon: "✳", description: "The Spring philanthropy 5K is tagged with this topic." },
    { id: "robotics-tag", type: "tags", x: 1147, y: 450, title: "Robotics", subtitle: "Topic", icon: "⌘", description: "Both Robotics Club and Robot demo day are tagged with this topic." },
    { id: "sports", type: "tags", x: 1147, y: 640, title: "Intramural sports", subtitle: "Topic · unused in this sample", icon: "◎", description: "A topic available in the seed data, not currently attached to an organization or event." },
    { id: "social", type: "tags", x: 1147, y: 830, title: "Social", subtitle: "Topic", icon: "♡", description: "The Gamma Chapter is tagged with this topic." },
    { id: "academic", type: "tags", x: 1147, y: 1020, title: "Academic", subtitle: "Topic · unused in this sample", icon: "✎", description: "A topic available in the seed data, not currently attached to an organization or event." },
];

const edges = [
    { from: "chapter", to: "national", type: "hierarchy", label: "chapter of", detail: "Staff-verified organization hierarchy." },
    { from: "chapter", to: "ifc", type: "hierarchy", label: "member of council", detail: "Staff-verified organization hierarchy." },
    { from: "ifc", to: "university", type: "hierarchy", label: "under institution", detail: "Staff-verified organization hierarchy." },
    { from: "robotics", to: "university", type: "hierarchy", label: "under institution", detail: "Staff-verified organization hierarchy." },
    { from: "avery", to: "chapter", type: "membership", label: "admin", detail: "Claimed and confirmed organization admin." },
    { from: "blake", to: "national", type: "membership", label: "admin", detail: "Claimed and confirmed organization admin." },
    { from: "casey", to: "robotics", type: "membership", label: "admin", detail: "Claimed and confirmed organization admin." },
    { from: "drew", to: "chapter", type: "membership", label: "officer", detail: "Confirmed chapter membership with Officer role." },
    { from: "emery", to: "robotics", type: "membership pending", label: "request pending", detail: "Membership request has not been confirmed." },
    { from: "chapter", to: "series", type: "hosting", label: "owns series", detail: "The chapter owns this recurring series." },
    { from: "series", to: "meeting1", type: "series", label: "occurrence", detail: "First published occurrence in the recurring series." },
    { from: "series", to: "meeting2", type: "series", detail: "Second published occurrence in the recurring series." },
    { from: "series", to: "meeting3", type: "series", detail: "Third published occurrence in the recurring series." },
    { from: "series", to: "meeting4", type: "series", detail: "Fourth published occurrence in the recurring series." },
    { from: "chapter", to: "fundraiser", type: "hosting", label: "primary host", detail: "The chapter is the primary host." },
    { from: "national", to: "fundraiser", type: "hosting", label: "co-host", detail: "Accepted co-host invitation." },
    { from: "robotics", to: "demo", type: "hosting", label: "primary host", detail: "The Robotics Club is the primary host." },
    { from: "chapter", to: "mixer", type: "hosting cancelled", label: "cancelled", detail: "The chapter hosted this cancelled event." },
    { from: "chapter", to: "formal", type: "hosting pending", label: "draft", detail: "The chapter owns this unpublished draft event." },
    { from: "fundraiser", to: "philanthropy", type: "topic", label: "tagged", detail: "Event topic tag." },
    { from: "robotics", to: "robotics-tag", type: "topic", label: "tagged", detail: "Organization topic tag." },
    { from: "demo", to: "robotics-tag", type: "topic", label: "tagged", detail: "Event topic tag." },
    { from: "chapter", to: "social", type: "topic", label: "tagged", detail: "Organization topic tag." },
];

const svg = document.querySelector("#graph");
const viewport = document.querySelector("#graph-viewport");
const inspectorEmpty = document.querySelector("#inspector-empty");
const inspectorContent = document.querySelector("#inspector-content");
const byId = new Map(nodes.map((node) => [node.id, node]));
const selectedLayers = new Set(Object.keys(columns));
let selectedId = null;

const SVG_NS = "http://www.w3.org/2000/svg";
const EDGE_LABELS = {
    hierarchy: "Hierarchy",
    membership: "Membership",
    hosting: "Hosts",
    series: "Series occurrence",
    topic: "Topic",
};
const TYPE_LABELS = { people: "Person", orgs: "Organization", events: "Event", tags: "Topic" };
const TYPE_ICONS = { people: "P", orgs: "O", events: "E", tags: "#" };
const nodeWidth = { people: 210, orgs: 270, events: 310, tags: 215 };
const nodeHeight = 50;

function svgElement(name, attrs = {}, text = "") {
    const element = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
    if (text) element.textContent = text;
    return element;
}

function nodePosition(node) {
    return {
        left: node.x,
        right: node.x + nodeWidth[node.type],
        centerY: node.y + nodeHeight / 2,
    };
}

function makeLanes() {
    for (const [type, lane] of Object.entries(columns)) {
        const group = svgElement("g", { class: `lane-group ${type}` });
        group.append(
            svgElement("rect", { class: "lane", x: lane.x, y: 25, width: lane.width, height: 1035, rx: 9 }),
            svgElement("text", { class: "lane-title", x: lane.x + 14, y: 48 }, lane.title),
            svgElement("text", { class: "lane-count", x: lane.x + lane.width - 26, y: 48, "text-anchor": "end" }, String(lane.count)),
        );
        svg.append(group);
    }
}

function makeEdges() {
    const group = svgElement("g", { class: "edges" });
    for (const [index, edge] of edges.entries()) {
        const from = byId.get(edge.from);
        const to = byId.get(edge.to);
        const start = nodePosition(from);
        const end = nodePosition(to);
        const sameLane = from.type === to.type;
        let x1;
        let x2;
        let path;
        if (sameLane) {
            x1 = start.right;
            x2 = end.right;
            const routeX = Math.max(start.right, end.right) + 35;
            path = `M ${x1} ${start.centerY} C ${routeX} ${start.centerY}, ${routeX} ${end.centerY}, ${x2} ${end.centerY}`;
        } else {
            const reversed = end.left < start.left;
            x1 = reversed ? start.left : start.right;
            x2 = reversed ? end.right : end.left;
            const bend = Math.max(28, Math.abs(x2 - x1) * 0.42);
            const direction = x2 >= x1 ? 1 : -1;
            path = `M ${x1} ${start.centerY} C ${x1 + bend * direction} ${start.centerY}, ${x2 - bend * direction} ${end.centerY}, ${x2} ${end.centerY}`;
        }
        const edgeGroup = svgElement("g", {
            class: `edge-group ${edge.type}`,
            "data-from": edge.from,
            "data-to": edge.to,
            tabindex: "0",
            role: "img",
            "aria-label": `${byId.get(edge.from).title} — ${edge.label || EDGE_LABELS[edge.type.split(" ")[0]]} — ${byId.get(edge.to).title}. ${edge.detail}`,
        });
        edgeGroup.append(
            svgElement("title", {}, `${byId.get(edge.from).title} → ${byId.get(edge.to).title}: ${edge.detail}`),
            svgElement("path", { class: `edge ${edge.type}`, d: path }),
        );
        if (edge.label) {
            const labelX = (x1 + x2) / 2;
            const labelY = (start.centerY + end.centerY) / 2 - 5 - (index % 2) * 7;
            edgeGroup.append(svgElement("text", { class: "edge-label", x: labelX, y: labelY, "text-anchor": "middle" }, edge.label));
        }
        edgeGroup.addEventListener("click", () => selectNode(edge.from));
        edgeGroup.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectNode(edge.from);
            }
        });
        group.append(edgeGroup);
    }
    svg.append(group);
}

function makeNode(node) {
    const width = nodeWidth[node.type];
    const group = svgElement("g", {
        class: `node ${node.type}`,
        transform: `translate(${node.x} ${node.y})`,
        tabindex: "0",
        role: "button",
        "aria-label": `${TYPE_LABELS[node.type]}: ${node.title}. ${node.subtitle}`,
        "data-id": node.id,
        "data-type": node.type,
    });
    group.append(
        svgElement("rect", { class: "node-card", width, height: nodeHeight, rx: 7 }),
        svgElement("rect", { class: "node-icon-bg", x: 9, y: 10, width: 30, height: 30, rx: 8 }),
        svgElement("text", { class: "node-icon", x: 24, y: 25 }, node.icon),
    );

    const hasBadge = Boolean(node.badge);
    const title = svgElement("text", { class: "node-title", x: 49, y: 21 });
    if (node.title.length > 27) {
        const firstLine = node.title.slice(0, 26).replace(/\s+\S*$/, "");
        title.setAttribute("y", "18");
        title.append(svgElement("tspan", { x: 49, dy: 0 }, firstLine));
        title.append(svgElement("tspan", { x: 49, dy: 11 }, node.title.slice(firstLine.length).trim()));
    } else {
        title.textContent = node.title;
    }
    group.append(title);
    group.append(svgElement("text", { class: "node-subtitle", x: 49, y: 37 }, node.subtitle));
    if (hasBadge) {
        const badgeWidth = node.badge.length * 4.5 + 12;
        const badgeX = width - badgeWidth - 8;
        group.append(
            svgElement("rect", { class: `node-badge-bg ${node.badgeTone || ""}`, x: badgeX, y: 8, width: badgeWidth, height: 14, rx: 4 }),
            svgElement("text", { class: "node-badge", x: badgeX + badgeWidth / 2, y: 17.5, "text-anchor": "middle" }, node.badge),
        );
    }
    group.addEventListener("click", () => selectNode(node.id));
    group.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            selectNode(node.id);
        }
    });
    return group;
}

function renderGraph() {
    makeLanes();
    makeEdges();
    for (const node of nodes) svg.append(makeNode(node));
    document.querySelector("#stat-nodes").textContent = String(nodes.length);
    document.querySelector("#stat-links").textContent = String(edges.length);
    document.querySelector("#stat-events").textContent = String(nodes.filter((node) => node.type === "events" && node.id !== "series").length);
}

function connectedNodes(nodeId) {
    return edges
        .filter((edge) => edge.from === nodeId || edge.to === nodeId)
        .map((edge) => {
            const otherId = edge.from === nodeId ? edge.to : edge.from;
            const other = byId.get(otherId);
            return { edge, other, relation: edge.label || EDGE_LABELS[edge.type.split(" ")[0]] };
        });
}

function renderInspector(nodeId) {
    const node = byId.get(nodeId);
    const connections = connectedNodes(nodeId);
    inspectorContent.replaceChildren();

    const detailType = document.createElement("span");
    detailType.className = `detail-type ${node.type}`;
    detailType.textContent = TYPE_LABELS[node.type];
    const title = document.createElement("h3");
    title.className = "detail-title";
    title.textContent = node.title;
    const subtitle = document.createElement("p");
    subtitle.className = "detail-subtitle";
    subtitle.textContent = node.subtitle;
    inspectorContent.append(detailType, title, subtitle);

    const description = document.createElement("p");
    description.className = `detail-note${node.badgeTone === "warning" ? " warning" : ""}`;
    description.textContent = node.description;
    inspectorContent.append(description);

    const divider = document.createElement("div");
    divider.className = "detail-divider";
    inspectorContent.append(divider);
    const sectionTitle = document.createElement("h4");
    sectionTitle.className = "detail-section-title";
    sectionTitle.textContent = `Connections · ${connections.length}`;
    inspectorContent.append(sectionTitle);

    const list = document.createElement("div");
    list.className = "connection-list";
    if (!connections.length) {
        const empty = document.createElement("p");
        empty.className = "detail-subtitle";
        empty.textContent = "No relationships in this sample.";
        list.append(empty);
    } else {
        for (const connection of connections) {
            const item = document.createElement("div");
            item.className = "connection-item";
            const icon = document.createElement("span");
            icon.className = `connection-icon ${connection.other.type}`;
            icon.textContent = TYPE_ICONS[connection.other.type];
            const text = document.createElement("span");
            const strong = document.createElement("strong");
            strong.textContent = connection.other.title;
            text.append(strong, document.createTextNode(` · ${connection.relation}`));
            item.append(icon, text);
            list.append(item);
        }
    }
    inspectorContent.append(list);
    inspectorEmpty.hidden = true;
    inspectorContent.hidden = false;
}

function selectNode(nodeId) {
    selectedId = nodeId;
    const neighborhood = new Set([nodeId]);
    for (const edge of edges) {
        if (edge.from === nodeId) neighborhood.add(edge.to);
        if (edge.to === nodeId) neighborhood.add(edge.from);
    }
    for (const element of svg.querySelectorAll(".node")) {
        const isSelected = element.dataset.id === nodeId;
        element.classList.toggle("selected", isSelected);
        element.classList.toggle("dimmed", !neighborhood.has(element.dataset.id));
        element.setAttribute("aria-pressed", String(isSelected));
    }
    for (const element of svg.querySelectorAll(".edge-group")) {
        const incident = element.dataset.from === nodeId || element.dataset.to === nodeId;
        element.querySelector(".edge").style.opacity = incident ? "1" : "";
        element.querySelector(".edge").style.strokeWidth = incident ? "2.5" : "";
    }
    renderInspector(nodeId);
}

function applyLayers() {
    for (const node of svg.querySelectorAll(".node")) {
        node.classList.toggle("hidden-layer", !selectedLayers.has(node.dataset.type));
    }
    for (const edge of svg.querySelectorAll(".edge-group")) {
        const from = byId.get(edge.dataset.from);
        const to = byId.get(edge.dataset.to);
        edge.classList.toggle("hidden-layer", !selectedLayers.has(from.type) || !selectedLayers.has(to.type));
    }
    if (selectedId && !selectedLayers.has(byId.get(selectedId).type)) {
        selectedId = null;
        for (const node of svg.querySelectorAll(".node")) node.classList.remove("selected", "dimmed");
        inspectorContent.hidden = true;
        inspectorEmpty.hidden = false;
    }
}

document.querySelectorAll(".layer-toggle").forEach((button) => {
    button.addEventListener("click", () => {
        const layer = button.dataset.layer;
        if (selectedLayers.has(layer)) selectedLayers.delete(layer);
        else selectedLayers.add(layer);
        button.classList.toggle("is-on", selectedLayers.has(layer));
        button.setAttribute("aria-pressed", String(selectedLayers.has(layer)));
        applyLayers();
    });
});

document.querySelector("#reset-view").addEventListener("click", () => {
    selectedId = null;
    for (const node of svg.querySelectorAll(".node")) node.classList.remove("selected", "dimmed");
    for (const edge of svg.querySelectorAll(".edge")) {
        edge.style.opacity = "";
        edge.style.strokeWidth = "";
    }
    for (const button of document.querySelectorAll(".layer-toggle")) {
        button.classList.add("is-on");
        button.setAttribute("aria-pressed", "true");
        selectedLayers.add(button.dataset.layer);
    }
    applyLayers();
    inspectorContent.hidden = true;
    inspectorEmpty.hidden = false;
    viewport.scrollTo({ left: 0, top: 0, behavior: "smooth" });
});

renderGraph();