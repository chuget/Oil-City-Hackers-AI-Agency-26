import {
  BedrockRuntimeClient,
  ConverseCommand,
} from "@aws-sdk/client-bedrock-runtime";
import { getAwsRegion, requireEnv } from "@/lib/aws/config";
import type { GovernedFinding } from "@/types/governance";

const client = new BedrockRuntimeClient({ region: getAwsRegion() });

export async function explainFinding(finding: GovernedFinding) {
  const modelId = requireEnv("BEDROCK_MODEL_ID");

  const command = new ConverseCommand({
    modelId,
    system: [
      {
        text:
          "You explain public-sector accountability findings. Keep the wording careful, concise, and bounded. Do not allege misconduct. Do not use the word fraud.",
      },
    ],
    messages: [
      {
        role: "user",
        content: [
          {
            text: [
              "Summarize this governed finding for a hackathon demo in 2-3 sentences.",
              "Mention the classification, why it was flagged, and the evidence still needed.",
              JSON.stringify(finding, null, 2),
            ].join("\n\n"),
          },
        ],
      },
    ],
    inferenceConfig: {
      maxTokens: 220,
      temperature: 0.2,
    },
  });

  const response = await client.send(command);
  return response.output?.message?.content?.map((part) => part.text ?? "").join("").trim() ?? "";
}
