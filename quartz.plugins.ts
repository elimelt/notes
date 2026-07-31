import { QuartzTransformerPlugin } from "./quartz/plugins/types"

export const StripFirstHeadingIfTitlePresent: QuartzTransformerPlugin = () => {
  return {
    name: "StripFirstHeadingIfTitlePresent",
    markdownPlugins() {
      return [
        () => {
          return (tree, file) => {
            if (!file.data.frontmatter?.title || !Array.isArray(tree.children)) {
              return
            }

            const firstHeadingIndex = tree.children.findIndex(
              (node) => node.type === "heading" && node.depth === 1,
            )

            if (firstHeadingIndex !== -1) {
              tree.children.splice(firstHeadingIndex, 1)
            }
          }
        },
      ]
    },
  }
}
