import { app } from "../../scripts/app.js";

// Simple extension for Prompt Library Loader
// Now just uses a dropdown menu, no complex UI needed
app.registerExtension({
    name: "comicverse.prompt_loader",
    async nodeCreated(node) {
        if (node.comfyClass !== "PromptLibraryLoaderNode") return;
        
        // Set a reasonable default size
        node.setSize([280, 80]);
    }
});
