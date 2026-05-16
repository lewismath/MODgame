const Network = (() => {
  let svg, linkSel, nodeSel;
  let xScale, yScale;
  let edgeSet; // Set of "u-v" strings for fast removal
  let degreeMap = {};

  const STATE_COLOR = { S: '#888888', red: '#e84040', blue: '#4080e8' };
  const MIN_R = 4, MAX_R = 14;

  function init(networkData) {
    const container = document.getElementById('graph-container');
    const W = container.clientWidth;
    const H = container.clientHeight;
    const PAD = 40;

    svg = d3.select('#graph')
      .attr('width', W)
      .attr('height', H);
    svg.selectAll('*').remove();

    const xs = networkData.nodes.map(n => n.x);
    const ys = networkData.nodes.map(n => n.y);
    xScale = d3.scaleLinear().domain([Math.min(...xs), Math.max(...xs)]).range([PAD, W - PAD]);
    yScale = d3.scaleLinear().domain([Math.min(...ys), Math.max(...ys)]).range([PAD, H - PAD]);

    // Precompute degree for radius scaling
    networkData.nodes.forEach(n => { degreeMap[n.id] = 0; });
    networkData.edges.forEach(([u, v]) => { degreeMap[u]++; degreeMap[v]++; });
    const maxDeg = Math.max(...Object.values(degreeMap), 1);
    const rScale = d3.scaleLinear().domain([0, maxDeg]).range([MIN_R, MAX_R]);

    edgeSet = new Set(networkData.edges.map(([u, v]) => edgeKey(u, v)));

    const g = svg.append('g');

    linkSel = g.append('g').attr('class', 'links')
      .selectAll('line')
      .data(networkData.edges)
      .join('line')
        .attr('x1', ([u]) => xScale(networkData.nodes[u].x))
        .attr('y1', ([u]) => yScale(networkData.nodes[u].y))
        .attr('x2', ([, v]) => xScale(networkData.nodes[v].x))
        .attr('y2', ([, v]) => yScale(networkData.nodes[v].y))
        .attr('stroke', '#444')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', 1.0)
        .attr('data-key', ([u, v]) => edgeKey(u, v));

    nodeSel = g.append('g').attr('class', 'nodes')
      .selectAll('circle')
      .data(networkData.nodes)
      .join('circle')
        .attr('cx', n => xScale(n.x))
        .attr('cy', n => yScale(n.y))
        .attr('r', n => rScale(degreeMap[n.id]))
        .attr('fill', STATE_COLOR.S)
        .attr('data-id', n => n.id);
  }

  function update(nodeStates) {
    nodeSel.attr('fill', n => STATE_COLOR[nodeStates[n.id]] || STATE_COLOR.S);
  }

  function removeEdges(edges) {
    edges.forEach(([u, v]) => {
      const key = edgeKey(u, v);
      edgeSet.delete(key);
    });
    linkSel.attr('stroke-opacity', function() {
      const key = d3.select(this).attr('data-key');
      return edgeSet.has(key) ? 1.0 : 0.0;
    });
  }

  function edgeKey(u, v) {
    return u < v ? `${u}-${v}` : `${v}-${u}`;
  }

  return { init, update, removeEdges };
})();
