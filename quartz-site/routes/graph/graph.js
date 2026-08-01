import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm"

const canvas = document.querySelector("#notes-graph")
const context = canvas.getContext("2d")
const status = document.querySelector("#graph-status")
const tooltip = document.querySelector("#graph-tooltip")
const fitButton = document.querySelector("#fit-graph")

const colors = {
  algorithms: "#28745b",
  hardware: "#b46a3c",
  math: "#477aa8",
  ml: "#a04f45",
  software: "#74733c",
  systems: "#4f6a8c",
  reference: "#8a694d",
  thoughts: "#7a655e",
  other: "#676b67",
}

let width = 0
let height = 0
let pixelRatio = 1
let transform = d3.zoomIdentity
let hovered = null
let nodes = []
let links = []
let simulation

function simplifySlug(value) {
  let slug = value.replace(/^\/+|\/+$/g, "")
  if (slug === "index") return ""
  if (slug.endsWith("/index")) slug = slug.slice(0, -6)
  return slug.replace(/\/+$/g, "")
}

function sectionFor(slug) {
  return slug.split("/")[0] || "other"
}

function nodeColor(node) {
  return colors[sectionFor(node.id)] ?? colors.other
}

function resize() {
  const bounds = canvas.getBoundingClientRect()
  width = bounds.width
  height = bounds.height
  pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)
  draw()
}

function graphBounds() {
  return {
    minX: d3.min(nodes, (node) => node.x) ?? 0,
    maxX: d3.max(nodes, (node) => node.x) ?? width,
    minY: d3.min(nodes, (node) => node.y) ?? 0,
    maxY: d3.max(nodes, (node) => node.y) ?? height,
  }
}

function fitGraph(animated = true) {
  if (!nodes.length) return
  const bounds = graphBounds()
  const graphWidth = Math.max(bounds.maxX - bounds.minX, 1)
  const graphHeight = Math.max(bounds.maxY - bounds.minY, 1)
  const scale = Math.min(2.2, 0.82 / Math.max(graphWidth / width, graphHeight / height))
  const x = width / 2 - scale * (bounds.minX + bounds.maxX) / 2
  const y = height / 2 - scale * (bounds.minY + bounds.maxY) / 2
  const next = d3.zoomIdentity.translate(x, y).scale(scale)
  const selection = d3.select(canvas)
  if (animated) selection.transition().duration(450).call(zoom.transform, next)
  else selection.call(zoom.transform, next)
}

function drawLabel(node, emphasized = false) {
  const fontSize = emphasized ? 13 : 10
  context.font = `${emphasized ? 600 : 500} ${fontSize}px "Noto Serif", serif`
  context.textAlign = "center"
  context.textBaseline = "bottom"
  context.fillStyle = getComputedStyle(document.documentElement).getPropertyValue("--ink")
  context.globalAlpha = emphasized ? 1 : 0.72
  context.fillText(node.title, node.x, node.y - 7, 240)
}

function draw() {
  if (!width || !height) return
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  context.clearRect(0, 0, width, height)
  context.save()
  context.translate(transform.x, transform.y)
  context.scale(transform.k, transform.k)

  const lineColor = getComputedStyle(document.documentElement).getPropertyValue("--line")
  context.strokeStyle = lineColor
  context.lineWidth = 0.8 / Math.sqrt(transform.k)
  context.beginPath()
  for (const link of links) {
    context.moveTo(link.source.x, link.source.y)
    context.lineTo(link.target.x, link.target.y)
  }
  context.stroke()

  for (const node of nodes) {
    const active = hovered === node
    const radius = (3.2 + Math.sqrt(node.degree) * 0.7) * (active ? 1.45 : 1)
    context.beginPath()
    context.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    context.fillStyle = nodeColor(node)
    context.globalAlpha = active ? 1 : 0.82
    context.fill()
  }

  const labelThreshold = transform.k > 1.45 ? 5 : 12
  for (const node of nodes) {
    if (node === hovered || node.degree >= labelThreshold) {
      drawLabel(node, node === hovered)
    }
  }

  context.restore()
  context.globalAlpha = 1
}

function graphPoint(event) {
  return transform.invert(d3.pointer(event, canvas))
}

function nearestNode(event, radius = 16) {
  if (!simulation) return null
  const [x, y] = graphPoint(event)
  const node = simulation.find(x, y, radius / transform.k)
  return node ?? null
}

function updateHover(event) {
  hovered = nearestNode(event)
  if (!hovered) {
    tooltip.hidden = true
    canvas.style.cursor = "grab"
  } else {
    tooltip.hidden = false
    tooltip.textContent = hovered.title
    tooltip.style.left = `${Math.min(event.clientX + 14, width - tooltip.offsetWidth - 12)}px`
    tooltip.style.top = `${Math.min(event.clientY + 14, height - tooltip.offsetHeight - 12)}px`
    canvas.style.cursor = "pointer"
  }
  draw()
}

const zoom = d3.zoom()
  .scaleExtent([0.15, 6])
  .filter((event) => !event.button && !nearestNode(event, 10))
  .on("zoom", (event) => {
    transform = event.transform
    tooltip.hidden = true
    draw()
  })

const drag = d3.drag()
  .subject((event) => nearestNode(event.sourceEvent, 18))
  .on("start", (event) => {
    if (!event.subject) return
    if (!event.active) simulation.alphaTarget(0.2).restart()
    event.subject.fx = event.subject.x
    event.subject.fy = event.subject.y
  })
  .on("drag", (event) => {
    if (!event.subject) return
    const [x, y] = transform.invert([event.x, event.y])
    event.subject.fx = x
    event.subject.fy = y
  })
  .on("end", (event) => {
    if (!event.subject) return
    if (!event.active) simulation.alphaTarget(0)
    event.subject.fx = null
    event.subject.fy = null
  })

async function loadGraph() {
  try {
    const response = await fetch("/static/contentIndex.json")
    if (!response.ok) throw new Error(`content index returned ${response.status}`)
    const content = await response.json()
    const bySlug = new Map()

    for (const [rawSlug, details] of Object.entries(content)) {
      const id = simplifySlug(rawSlug)
      bySlug.set(id, { id, title: details.title || id || "Home", degree: 0 })
    }

    const seen = new Set()
    for (const [rawSlug, details] of Object.entries(content)) {
      const source = simplifySlug(rawSlug)
      for (const rawTarget of details.links ?? []) {
        const target = simplifySlug(rawTarget)
        if (!bySlug.has(target) || source === target) continue
        const key = source < target ? `${source}\u0000${target}` : `${target}\u0000${source}`
        if (seen.has(key)) continue
        seen.add(key)
        bySlug.get(source).degree += 1
        bySlug.get(target).degree += 1
        links.push({ source, target })
      }
    }

    nodes = [...bySlug.values()].filter((node) => node.degree > 0)
    const connected = new Set(nodes.map((node) => node.id))
    links = links.filter((link) => connected.has(link.source) && connected.has(link.target))
    status.textContent = `${nodes.length} notes · ${links.length} links`

    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((node) => node.id).distance(76).strength(0.18))
      .force("charge", d3.forceManyBody().strength(-105).distanceMax(800))
      .force("collide", d3.forceCollide().radius((node) => 9 + Math.sqrt(node.degree) * 1.4).iterations(3))
      .force("x", d3.forceX(width / 2).strength(0.012))
      .force("y", d3.forceY(height / 2).strength(0.012))
      .on("tick", draw)
      .on("end", () => fitGraph(false))
  } catch (error) {
    console.error(error)
    status.textContent = "Graph unavailable"
  }
}

d3.select(canvas).call(zoom).call(drag)
canvas.addEventListener("pointermove", updateHover)
canvas.addEventListener("pointerleave", () => {
  hovered = null
  tooltip.hidden = true
  draw()
})
canvas.addEventListener("click", (event) => {
  const node = nearestNode(event)
  if (!node) return
  const target = new URLSearchParams(window.location.search).get("target") === "top" ? "_top" : "_blank"
  const url = node.id ? `/${node.id}` : "/"
  window.open(url, target, "noopener")
})
fitButton.addEventListener("click", () => fitGraph())
new ResizeObserver(resize).observe(canvas)
resize()
loadGraph()
