// Quartz transformer plugin.
//
// The @quartz-community/latex plugin (with katexOptions.output "htmlAndMathml")
// renders each math expression as a `.katex` element containing a visual
// `.katex-html` subtree and a screen-reader `.katex-mathml` subtree. The latter
// holds an <annotation encoding="application/x-tex"> node with the exact source
// LaTeX. This transformer copies that LaTeX onto the `.katex` element as a
// `data-tex` attribute so downstream consumers (e.g. the TTS reader) can read
// the source without parsing MathML, then drops the now-redundant MathML
// subtree to keep the DOM lean. The visual rendering is untouched.

const hasClass = (node, name) => {
  const c = node.properties && node.properties.className
  if (!c) return false
  return Array.isArray(c) ? c.includes(name) : String(c).split(/\s+/).includes(name)
}

const collectText = node => {
  if (!node) return ""
  if (node.type === "text") return node.value || ""
  if (!node.children) return ""
  let out = ""
  for (const child of node.children) out += collectText(child)
  return out
}

const findAnnotation = node => {
  if (!node || node.type !== "element") return null
  if (
    node.tagName === "annotation" &&
    node.properties &&
    node.properties.encoding === "application/x-tex"
  ) {
    return node
  }
  if (!node.children) return null
  for (const child of node.children) {
    const found = findAnnotation(child)
    if (found) return found
  }
  return null
}

const transform = node => {
  if (!node || node.type !== "element") {
    if (node && node.children) node.children.forEach(transform)
    return
  }

  if (hasClass(node, "katex")) {
    const annotation = findAnnotation(node)
    const tex = annotation ? collectText(annotation).trim() : ""
    if (tex) {
      node.properties = node.properties || {}
      node.properties["dataTex"] = tex
    }
    if (node.children) {
      node.children = node.children.filter(child => !hasClass(child, "katex-mathml"))
    }
  }

  if (node.children) node.children.forEach(transform)
}

const rehypeMathTexSource = () => tree => {
  transform(tree)
  return tree
}

export default () => ({
  name: "MathTexSource",
  htmlPlugins() {
    return [rehypeMathTexSource]
  },
})
