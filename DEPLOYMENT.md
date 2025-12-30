# AWS Fargate Deployment Guide (RSS Feed + S3)

This guide details how to deploy `yt-digest` to AWS Fargate. The application will fetch its configuration from an S3 bucket, generate an RSS feed, and upload the result back to S3.

## Prerequisites

1.  **AWS Account**: Access to the AWS Console.
2.  **AWS CLI**: Configured locally.
3.  **Docker**: Installed locally.
4.  **S3 Bucket**: You must have the bucket `ytdigest` created.

---

## Step 1: Update Requirements and Rebuild Image

We need to include the `awscli` in the Docker image so the container can execute S3 commands to download the config and upload the feed.

1.  **Add `awscli` to `requirements.txt`**:
    Open `requirements.txt` and add `awscli` to the list of dependencies.
    ```text
    scrapetube==2.6.0
    youtube-transcript-api==1.2.3
    python-dotenv==1.2.1
    openai==2.9.0
    markdown==3.10
    # ... other existing items ...
    awscli
    ```

2.  **Authenticate with ECR**:
    ```bash
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
    ```

3.  **Build and Push the Image**:
    ```bash
    # Build the image
    docker build -t yt-digest .

    # Tag the image
    docker tag yt-digest:latest <YOUR_ACCOUNT_ID>[.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest](https://.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest)

    # Push to AWS
    docker push <YOUR_ACCOUNT_ID>[.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest](https://.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest)
    ```

---

## Step 2: Prepare S3 Bucket

1.  **Upload Configuration**:
    Create your `queries.json` locally and upload it to your bucket.
    ```bash
    aws s3 cp queries.json s3://ytdigest/queries.json
    ```

2.  **Public Access (Optional)**:
    If you want to subscribe to this feed using a reader like Feedly, the `feed.xml` file usually needs to be publicly accessible.
    * **Option A (Bucket Policy)**: Go to S3 Console > `ytdigest` > Permissions > Bucket Policy and allow `s3:GetObject` on `feed.xml` for `*`.
    * **Option B (ACLs)**: If your bucket allows ACLs, you can set the file to public during upload (included in the command in Step 4).

---

## Step 3: Configure IAM Permissions

Your Fargate task needs permission to **Read** the config and **Write** the feed.

1.  Go to **IAM Console** > **Roles**.
2.  Find (or create) your **ECS Task Role** (e.g., `ecsTaskRole`).
3.  **Attach Policy** (Inline) with these permissions:
    ```json
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                "Resource": "arn:aws:s3:::ytdigest/*"
            }
        ]
    }
    ```

---

## Step 4: Create ECS Task Definition

1.  Go to **Amazon ECS Console** > **Task Definitions** > **Create new Task Definition**.
2.  **Family**: `yt-digest-rss`.
3.  **Launch Type**: **AWS Fargate**.
4.  **Task Role**: Select the IAM Role configured in Step 3.
5.  **Task Execution Role**: Select `ecsTaskExecutionRole`.
6.  **Container Details**:
    * **Image**: `<YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest`
    * **Command**: This command downloads the config, runs the app, and uploads the feed with the correct content type.
        ```bash
        sh,-c,aws s3 cp s3://ytdigest/queries.json . && python app.py && aws s3 cp feed.xml s3://ytdigest/feed.xml --content-type "application/rss+xml"
        ```
        *(Note: If you rely on ACLs for public access, append ` --acl public-read` to the end of the command above).*
7.  **Environment Variables**:
    * `OPENAI_API_KEY`: `sk-...`
    * `PROXY_USERNAME`: `...`
    * `PROXY_PASSWORD`: `...`
    * `FEED_BASE_URL`: `https://ytdigest.s3.amazonaws.com/` (or your custom domain)

---

## Step 5: Schedule with EventBridge

1.  Go to **Amazon EventBridge** > **Schedules** > **Create Schedule**.
2.  **Schedule**: Cron-based (e.g., `0 7 * * ? *` for daily at 7 AM).
3.  **Target**: **Amazon ECS** > **Run Task**.
4.  **Configuration**:
    * **Cluster**: Your Fargate cluster.
    * **Task Definition**: `yt-digest-rss` (LATEST).
    * **Subnets**: Public Subnet (Auto-assign Public IP: **ENABLED**).

---

## Accessing Your Feed

Once the task runs successfully, your RSS feed will be available at:

* **Standard S3 URL**: `https://ytdigest.s3.amazonaws.com/feed.xml`
* *(Or your region-specific endpoint if not US-East-1)*