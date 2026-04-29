import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getAwsClientConfig, getAwsRegion, requireEnv } from "@/lib/aws/config";

const client = new S3Client(getAwsClientConfig());

export async function putJsonSnapshot(key: string, payload: unknown) {
  const bucket = requireEnv("CASE_EXPORT_BUCKET");

  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: key,
      Body: JSON.stringify(payload, null, 2),
      ContentType: "application/json",
      ServerSideEncryption: "AES256",
    }),
  );

  return {
    bucket,
    key,
    region: getAwsRegion(),
  };
}
