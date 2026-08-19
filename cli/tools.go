package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"

	"google.golang.org/genai"
)

// GBrainResult maps to the JSON structure returned by `gbrain query --json`
type GBrainResult struct {
	Slug      string  `json:"slug"`
	Score     float64 `json:"score"`
	SourceID  string  `json:"source_id"`
	ChunkText string  `json:"chunk_text"`
	Title     string  `json:"title"`
}

func GetTools() []*genai.Tool {
	return []*genai.Tool{
		{
			FunctionDeclarations: []*genai.FunctionDeclaration{
				{
					Name:        "search_gmail_facts",
					Description: "An intent-rich natural language query to search the user's Gmail history. Use this when the user asks about emails, messages, senders, or conversations.",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"query": {Type: genai.TypeString, Description: "A standalone, intent-rich query to search Gmail."},
						},
						Required: []string{"query"},
					},
				},
				{
					Name:        "search_drive_facts",
					Description: "An intent-rich natural language query to search the user's Google Drive files. Use this when the user asks about documents, reports, notes, or files.",
					Parameters: &genai.Schema{
						Type: genai.TypeObject,
						Properties: map[string]*genai.Schema{
							"query": {Type: genai.TypeString, Description: "A standalone, intent-rich query to search Drive."},
						},
						Required: []string{"query"},
					},
				},
			},
		},
	}
}

func ExecuteTool(ctx context.Context, name string, args map[string]any) string {
	query, ok := args["query"].(string)
	if !ok || query == "" {
		return "Error: missing query argument."
	}

	source := ""
	switch name {
	case "search_gmail_facts":
		source = "gmail"
	case "search_drive_facts":
		source = "drive"
	default:
		return fmt.Sprintf("Error: unknown tool %s", name)
	}

	// Query gbrain using the registered source ID and request JSON output for full context
	cmd := exec.CommandContext(ctx, "gbrain", "query", query, "--source-id", source, "--json")

	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	if err != nil {
		return fmt.Sprintf("Error executing gbrain query: %v\nStderr: %s", err, stderr.String())
	}

	outStr := stdout.String()

	// Robust JSON extraction: find the first '[' and last ']' to ignore any potential log noise printed to stdout
	startIdx := strings.Index(outStr, "[")
	endIdx := strings.LastIndex(outStr, "]")

	if startIdx == -1 || endIdx == -1 || endIdx <= startIdx {
		return fmt.Sprintf("Could not find valid JSON array in gbrain output.\nRaw output: %s", outStr)
	}

	jsonStr := outStr[startIdx : endIdx+1]

	var results []GBrainResult
	if err := json.Unmarshal([]byte(jsonStr), &results); err != nil {
		return fmt.Sprintf("Error parsing gbrain JSON output: %v\nRaw JSON: %s", err, jsonStr)
	}

	if len(results) == 0 {
		return fmt.Sprintf("No results found in %s for query: %s", source, query)
	}

	// Extract top 2 chunk_texts to provide focused, un-truncated context to the LLM
	var formattedResults []string
	limit := 2
	if len(results) < limit {
		limit = len(results)
	}

	for i := 0; i < limit; i++ {
		r := results[i]
		// We include the score so the LLM can weigh the relevance of the evidence
		formattedResults = append(formattedResults, fmt.Sprintf("Source: %s | Document: %s (Relevance Score: %.4f)\nContent:\n%s", source, r.Slug, r.Score, r.ChunkText))
	}

	return strings.Join(formattedResults, "\n\n---\n\n")
}
