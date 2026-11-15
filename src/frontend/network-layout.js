"use strict";

// Where everything sits on the network map. Pure maths, no DOM:
//   Collectivize.NetworkLayout.arrange(map, random?, footprint?) -> { center, orgs, people, links, reach }
//
// The node in focus is pinned at (0, 0). Everything else starts at a
// random spot and is then pulled into place, as far out as it needs to go
// (the page shows a fixed-size circle of it and lets you move around;
// `reach` is how far the furthest node ended up from the middle):
//   - every node is tied to the center, on a shorter tie the more it
//     shares with the center (its `closeness`), so close ones sit nearer;
//   - people who are connected to each other are tied together, so
//     friends end up side by side; people who are only close in the
//     network (map.near) are tied more loosely; so are people and the
//     communities shown that they belong to (map.memberships);
//   - all nodes push each other apart so nothing overlaps;
//   - nobody comes nearer the center than CENTER_GAP, so no node ever
//     touches the middle node or covers its label.
// The starting spots are random, so the same network is drawn a little
// differently each time. Pass a `random` function to make it repeatable.

(() => {
    const STEPS = 320;
    const FAR = 175; // tie to the center for a node that shares nothing with it
    const NEAR = 125; // ...and for one that shares a lot
    // Closest any node may sit to the center: the middle node (radius 34)
    // and its label below it, plus a person node (radius 21) and a gap.
    const CENTER_GAP = 115;
    const PEER_TIE = 90; // between two connected people
    const NEAR_TIE = 125; // between two people who are close but not connected
    const PUSH = 5200; // how hard nodes push each other apart
    const MIN_GAP = 74; // nodes closer than this are pushed apart firmly
    const CENTER_PULL = 0.05;
    const PEER_PULL = 0.03;
    const NEAR_PULL = 0.012;
    const MEMBER_TIE = 115; // between a person and a community they belong to
    const MEMBER_PULL = 0.012;

    const LABEL_PAD = 6; // space kept between two footprints
    const CLEAR_STEPS = 400;

    const clamp = (value, limit) => Math.min(limit, Math.max(-limit, value));

    /**
     * Move nodes until no two footprints overlap. A footprint is a box around
     * a node: `half` its width either side, `up` above and `down` below its
     * middle (the name sits underneath). The center never moves; when two
     * boxes overlap, they part along whichever way needs the smaller move.
     */
    function clearLabels(spots, centerBox) {
        const boxes = [{ x: 0, y: 0, ...centerBox, fixed: true }, ...spots];
        for (let step = 0; step < CLEAR_STEPS; step += 1) {
            let moved = false;
            for (let i = 0; i < boxes.length; i += 1) {
                for (let j = i + 1; j < boxes.length; j += 1) {
                    const a = boxes[i];
                    const b = boxes[j];
                    const overlapX = a.half + b.half + LABEL_PAD - Math.abs(a.x - b.x);
                    const overlapY = Math.min(a.y + a.down, b.y + b.down)
                        - Math.max(a.y - a.up, b.y - b.up) + LABEL_PAD;
                    if (overlapX <= 0 || overlapY <= 0) continue;
                    moved = true;
                    // Part sideways or up/down, whichever is the shorter move.
                    const sideways = overlapX < overlapY;
                    const sign = sideways
                        ? (b.x - a.x || (j % 2 ? 1 : -1)) > 0 ? 1 : -1
                        : (b.y - a.y || (j % 2 ? 1 : -1)) > 0 ? 1 : -1;
                    const amount = (sideways ? overlapX : overlapY) + 0.5;
                    const shareA = a.fixed ? 0 : b.fixed ? 1 : 0.5;
                    const axis = sideways ? "x" : "y";
                    a[axis] -= sign * amount * shareA;
                    b[axis] += sign * amount * (1 - shareA);
                }
            }
            if (!moved) break;
        }
    }

    /** Tie length to the center: shorter the more the node shares with it. */
    const tieLength = (closeness, most) => (most > 0 ? FAR - (FAR - NEAR) * (closeness / most) : (FAR + NEAR) / 2);

    function arrange(map, random = Math.random, footprint = null) {
        const center = { x: 0, y: 0 };
        const nodes = [...map.orgs.map((org) => ({ ...org, isOrg: true })), ...map.people];
        const most = Math.max(0, ...nodes.map((node) => node.closeness));
        // Crowded maps get longer ties so the rings don't jam.
        const stretch = 1 + Math.max(0, nodes.length - 14) * 0.025;

        const spots = nodes.map((node) => {
            const angle = random() * Math.PI * 2;
            const distance = 70 + random() * 110;
            return {
                node,
                x: center.x + Math.cos(angle) * distance,
                y: center.y + Math.sin(angle) * distance,
                tie: tieLength(node.closeness, most) * stretch,
            };
        });
        const byId = new Map(spots.map((spot) => [spot.node.id, spot]));
        const tied = (pairs, kind, length, pull) => (pairs || [])
            .map(([a, b]) => ({ a: byId.get(a), b: byId.get(b), kind, length, pull }))
            .filter((tie) => tie.a && tie.b);
        const ties = [
            ...tied(map.links, "peer", PEER_TIE, PEER_PULL),
            ...tied(map.near, "near", NEAR_TIE, NEAR_PULL),
            ...tied(map.memberships, "org", MEMBER_TIE, MEMBER_PULL),
        ];
        // Someone tied to many others is pulled less by each, so a tightly
        // knit group gathers on one side without collapsing into a clump.
        const tieCount = new Map();
        for (const tie of ties) {
            for (const end of [tie.a, tie.b]) tieCount.set(end, (tieCount.get(end) || 0) + 1);
        }
        for (const tie of ties) {
            tie.pull /= Math.max(1, Math.sqrt(tieCount.get(tie.a) * tieCount.get(tie.b)) / 2);
        }

        for (let step = 0; step < STEPS; step += 1) {
            const cooling = 1 - step / STEPS;
            const moves = spots.map(() => ({ x: 0, y: 0 }));
            spots.forEach((spot, i) => {
                // Tie to the center.
                const dx = spot.x - center.x;
                const dy = spot.y - center.y;
                const length = Math.hypot(dx, dy) || 1;
                const pull = (length - spot.tie) * CENTER_PULL;
                moves[i].x -= (dx / length) * pull;
                moves[i].y -= (dy / length) * pull;
                // Push away from every other node.
                for (let j = i + 1; j < spots.length; j += 1) {
                    const gx = spot.x - spots[j].x;
                    const gy = spot.y - spots[j].y;
                    const gap = Math.hypot(gx, gy) || 1;
                    const push = PUSH / (gap * gap) + (gap < MIN_GAP ? (MIN_GAP - gap) * 0.3 : 0);
                    moves[i].x += (gx / gap) * push;
                    moves[i].y += (gy / gap) * push;
                    moves[j].x -= (gx / gap) * push;
                    moves[j].y -= (gy / gap) * push;
                }
            });
            for (const tie of ties) {
                const { a, b } = tie;
                const dx = b.x - a.x;
                const dy = b.y - a.y;
                const length = Math.hypot(dx, dy) || 1;
                const pull = (length - tie.length) * tie.pull;
                const ia = spots.indexOf(a);
                const ib = spots.indexOf(b);
                moves[ia].x += (dx / length) * pull;
                moves[ia].y += (dy / length) * pull;
                moves[ib].x -= (dx / length) * pull;
                moves[ib].y -= (dy / length) * pull;
            }
            spots.forEach((spot, i) => {
                const limit = 4 + 26 * cooling; // big moves early, small ones late
                spot.x += clamp(moves[i].x, limit);
                spot.y += clamp(moves[i].y, limit);
                // Hard buffer: anyone pulled inside CENTER_GAP is put back on it.
                const distance = Math.hypot(spot.x - center.x, spot.y - center.y);
                if (distance < CENTER_GAP) {
                    const angle = distance > 0.01 ? Math.atan2(spot.y - center.y, spot.x - center.x) : random() * Math.PI * 2;
                    spot.x = center.x + Math.cos(angle) * CENTER_GAP;
                    spot.y = center.y + Math.sin(angle) * CENTER_GAP;
                }
            });
        }

        // Last, keep every node and the name under it clear of every other one
        // (and of the middle). Lost in merge 0dcc30f; restored.
        if (footprint) {
            for (const spot of spots) Object.assign(spot, footprint(spot.node, false));
            clearLabels(spots, footprint(map.center, true));
        }

        const placed = spots.map((spot) => ({ ...spot.node, x: spot.x, y: spot.y }));
        // The middle's own ties: one line to each person and community shown.
        // Connections between the people shown, and each person's line to the
        // communities shown that they belong to ("mutual"), are returned too;
        // the page draws them only when "Mutual connections" is switched on.
        const at = new Map(placed.map((node) => [node.id, node]));
        const links = [
            ...placed.map((node) => ({ from: center, to: node, kind: "direct" })),
            ...ties.filter((tie) => tie.kind === "peer" || tie.kind === "org")
                .map((tie) => ({ from: at.get(tie.a.node.id), to: at.get(tie.b.node.id), kind: "mutual" })),
        ];
        return {
            center: { ...map.center, ...center },
            orgs: placed.filter((node) => node.isOrg),
            people: placed.filter((node) => !node.isOrg),
            links,
            reach: Math.max(0, ...placed.map((node) => Math.hypot(node.x, node.y))),
        };
    }

    window.Collectivize = Object.freeze({ ...window.Collectivize, NetworkLayout: Object.freeze({ arrange }) });
})();
