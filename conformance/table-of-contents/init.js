import TableOfContents from "../../src/js/components/table-of-contents.js";

export const instances = Array.from(document.querySelectorAll("[data-toc]"))
  .map((element) => TableOfContents.getOrCreateInstance(element));
