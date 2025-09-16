import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import "./MovieNetwork.css";

const MovieNetwork = ({ networkData, onNodeClick }) => {
  const svgRef = useRef();
  const containerRef = useRef();
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  useEffect(() => {
    if (!networkData || !containerRef.current) return;

    const container = containerRef.current;
    const containerRect = container.getBoundingClientRect();
    const width = Math.max(800, containerRect.width);
    const height = Math.max(600, Math.min(800, window.innerHeight - 200));

    // Clear previous visualization
    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Add gradient definitions
    const defs = svg.append("defs");
    
    // Central node gradient
    const centralGradient = defs.append("radialGradient")
      .attr("id", "central-gradient")
      .attr("cx", "50%")
      .attr("cy", "50%")
      .attr("r", "50%");
    
    centralGradient.append("stop")
      .attr("offset", "0%")
      .attr("stop-color", "#ff6b9d")
      .attr("stop-opacity", 1);
    
    centralGradient.append("stop")
      .attr("offset", "100%")
      .attr("stop-color", "#c44569")
      .attr("stop-opacity", 1);

    // Related node gradient
    const relatedGradient = defs.append("radialGradient")
      .attr("id", "related-gradient")
      .attr("cx", "50%")
      .attr("cy", "50%")
      .attr("r", "50%");
    
    relatedGradient.append("stop")
      .attr("offset", "0%")
      .attr("stop-color", "#74b9ff")
      .attr("stop-opacity", 1);
    
    relatedGradient.append("stop")
      .attr("offset", "100%")
      .attr("stop-color", "#0984e3")
      .attr("stop-opacity", 1);

    // Prepare data
    const centralNode = {
      ...networkData.central_movie,
      type: "central",
      x: width / 2,
      y: height / 2,
      fx: width / 2,
      fy: height / 2
    };

    const relatedNodes = networkData.related_movies.map((movie, index) => ({
      ...movie,
      type: "related",
      index
    }));

    const nodes = [centralNode, ...relatedNodes];
    
    // Create links from central to all related nodes
    const links = relatedNodes.map(node => ({
      source: centralNode,
      target: node
    }));

    // Create force simulation
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(200))
      .force("charge", d3.forceManyBody().strength(-500))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(70));

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svg.call(zoom);

    // Create main group
    const g = svg.append("g");

    // Create links
    const link = g.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("class", "network-link")
      .attr("stroke", "rgba(255, 255, 255, 0.3)")
      .attr("stroke-width", 2);

    // Create node groups
    const nodeGroup = g.append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("class", d => `network-node ${d.type}`)
      .style("cursor", d => d.type === "central" ? "default" : "pointer")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add node circles (backgrounds)
    nodeGroup.append("circle")
      .attr("r", d => d.type === "central" ? 80 : 60)
      .attr("fill", d => d.type === "central" ? "url(#central-gradient)" : "url(#related-gradient)")
      .attr("stroke", "rgba(255, 255, 255, 0.8)")
      .attr("stroke-width", d => d.type === "central" ? 4 : 2)
      .style("filter", "drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3))");

    // Add movie poster images
    nodeGroup.append("clipPath")
      .attr("id", (d, i) => `clip-${i}`)
      .append("circle")
      .attr("r", d => d.type === "central" ? 70 : 50);

    nodeGroup.append("image")
      .attr("href", d => d.poster_url || "/api/placeholder/140/210")
      .attr("x", d => d.type === "central" ? -70 : -50)
      .attr("y", d => d.type === "central" ? -70 : -50)
      .attr("width", d => d.type === "central" ? 140 : 100)
      .attr("height", d => d.type === "central" ? 140 : 100)
      .attr("clip-path", (d, i) => `url(#clip-${i})`)
      .style("opacity", 0.9);

    // Add node labels
    nodeGroup.append("text")
      .attr("class", "node-label")
      .attr("text-anchor", "middle")
      .attr("y", d => d.type === "central" ? 95 : 75)
      .style("fill", "#ffffff")
      .style("font-size", d => d.type === "central" ? "14px" : "12px")
      .style("font-weight", "600")
      .style("text-shadow", "0 2px 4px rgba(0, 0, 0, 0.8)")
      .text(d => {
        const maxLength = d.type === "central" ? 20 : 15;
        return d.title.length > maxLength ? 
          d.title.substring(0, maxLength) + "..." : 
          d.title;
      });

    // Add rating badges
    nodeGroup.filter(d => d.vote_average)
      .append("g")
      .attr("class", "rating-badge")
      .attr("transform", d => d.type === "central" ? "translate(55, -55)" : "translate(40, -40)")
      .call(g => {
        g.append("circle")
          .attr("r", 18)
          .attr("fill", "rgba(255, 255, 255, 0.9)")
          .attr("stroke", "#ffd700")
          .attr("stroke-width", 2);
        
        g.append("text")
          .attr("text-anchor", "middle")
          .attr("dy", "0.35em")
          .style("fill", "#333")
          .style("font-size", "11px")
          .style("font-weight", "700")
          .text(d => d.vote_average.toFixed(1));
      });

    // Mouse events
    nodeGroup
      .on("mouseover", function(event, d) {
        if (d.type !== "central") {
          setHoveredNode(d);
          d3.select(this).select("circle")
            .transition()
            .duration(200)
            .attr("r", 70)
            .style("filter", "drop-shadow(0 6px 16px rgba(0, 0, 0, 0.4))");
        }
      })
      .on("mouseout", function(event, d) {
        if (d.type !== "central") {
          setHoveredNode(null);
          d3.select(this).select("circle")
            .transition()
            .duration(200)
            .attr("r", 60)
            .style("filter", "drop-shadow(0 4px 12px rgba(0, 0, 0, 0.3))");
        }
      })
      .on("click", function(event, d) {
        event.stopPropagation();
        if (d.type !== "central") {
          setSelectedNode(d);
          onNodeClick(d.id);
        }
      });

    // Update positions on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      nodeGroup
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      if (d.type !== "central") {
        d.fx = null;
        d.fy = null;
      }
    }

    // Cleanup
    return () => {
      simulation.stop();
    };

  }, [networkData, onNodeClick]);

  if (!networkData) {
    return null;
  }

  return (
    <div className="movie-network" ref={containerRef}>
      <div className="network-header">
        <h2 className="network-title">Movie Network</h2>
        <p className="network-subtitle">
          Click on any movie to explore its connections
        </p>
      </div>
      
      <div className="network-container">
        <svg ref={svgRef} className="network-svg"></svg>
        
        {hoveredNode && (
          <div className="movie-tooltip">
            <h3>{hoveredNode.title}</h3>
            <p className="tooltip-year">
              {hoveredNode.release_date ? new Date(hoveredNode.release_date).getFullYear() : 'N/A'}
            </p>
            <div className="tooltip-rating">
              <span>⭐ {hoveredNode.vote_average ? hoveredNode.vote_average.toFixed(1) : 'N/A'}</span>
            </div>
            <p className="tooltip-overview">
              {hoveredNode.overview 
                ? hoveredNode.overview.length > 150 
                  ? hoveredNode.overview.substring(0, 150) + "..."
                  : hoveredNode.overview
                : "No overview available"
              }
            </p>
          </div>
        )}
      </div>

      <div className="network-controls">
        <div className="control-hint">
          <span>💡 Drag nodes • Zoom with mouse wheel • Click to explore</span>
        </div>
      </div>
    </div>
  );
};

export default MovieNetwork;