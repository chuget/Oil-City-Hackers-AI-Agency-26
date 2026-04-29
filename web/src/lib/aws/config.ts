export function getAwsRegion() {
  return (
    process.env.HACKATHON_AWS_REGION ??
    process.env.AWS_REGION ??
    process.env.AWS_DEFAULT_REGION ??
    "us-west-2"
  );
}

export function getAwsClientConfig() {
  const accessKeyId =
    process.env.HACKATHON_AWS_ACCESS_KEY_ID ?? process.env.AWS_ACCESS_KEY_ID;
  const secretAccessKey =
    process.env.HACKATHON_AWS_SECRET_ACCESS_KEY ?? process.env.AWS_SECRET_ACCESS_KEY;
  const sessionToken =
    process.env.HACKATHON_AWS_SESSION_TOKEN ?? process.env.AWS_SESSION_TOKEN;

  if (accessKeyId && secretAccessKey) {
    return {
      region: getAwsRegion(),
      credentials: {
        accessKeyId,
        secretAccessKey,
        sessionToken,
      },
    };
  }

  return { region: getAwsRegion() };
}

export function requireEnv(name: string) {
  const value = process.env[name];

  if (!value) {
    throw new Error(`${name} is not configured`);
  }

  return value;
}
