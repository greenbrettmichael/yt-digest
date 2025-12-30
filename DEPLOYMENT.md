# AWS Fargate Deployment Guide (RSS Feed + S3)

This guide details how to deploy `yt-digest` to AWS Fargate. The application will fetch its configuration from an S3 bucket, generate an RSS feed, and upload the result back to S3.

## Prerequisites

1.  **AWS Account**: Access to the AWS Console.
2.  **AWS CLI**: Configured locally.
3.  **Docker**: Installed locally.
4.  **S3 Bucket**: You must have the bucket `ytdigest` created.

---

## Step 1: Configure Local User Permissions

Your local IAM user (the one you use with `aws configure`) needs permission to push Docker images and upload configuration files.

1.  Log in to the **AWS Console** and go to **IAM** > **Users**.
2.  Select your user (e.g., `ytdigest`).
3.  Click **Add permissions** > **Attach policies directly**.
4.  Add the following policies:
    * **`AmazonEC2ContainerRegistryFullAccess`** (Required to create repos and push images)
    * **`AmazonS3FullAccess`** (Required to upload `queries.json`)
    * *(Alternatively, you can create tighter custom policies, but these ensure smooth deployment).*

---

## Step 2: Build and Push Docker Image

1.  **Authenticate with ECR**:
    ```bash
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
    ```

2.  **Create Repository (if not exists)**:
    ```bash
    aws ecr create-repository --repository-name yt-digest --region us-east-1
    ```

3.  **Build and Push**:
    ```bash
    # Build the image
    docker build -t yt-digest .

    # Tag the image (using your specific account URL)
    docker tag yt-digest:latest <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest

    # Push to AWS
    docker push <YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest
    ```

---

## Step 3: Prepare S3 Bucket

1.  **Upload Configuration**:
    Create your `queries.json` locally and upload it to your bucket.
    ```bash
    aws s3 cp queries.json s3://ytdigest/queries.json
    ```

2.  **Public Access (Optional)**:
    If you want to subscribe to this feed using a reader like Feedly, the `feed.xml` file usually needs to be publicly accessible.
    * **Option A (Bucket Policy)**: Go to S3 Console > `ytdigest` > Permissions > Bucket Policy and allow `s3:GetObject` on `feed.xml` for `*`.
    * **Option B (ACLs)**: If your bucket allows ACLs, the deployment command can set the file to public during upload.

---

## Step 4: Configure ECS Task Role Permissions

The **Task Role** is used by the *running container* to read/write to S3.

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

## Step 5: Create ECS Task Definition

1.  Go to **Amazon ECS Console** > **Task Definitions** > **Create new Task Definition**.
2.  **Family**: `yt-digest-rss`.
3.  **Launch Type**: **AWS Fargate**.
4.  **Task Role**: Select the IAM Role configured in Step 4.
5.  **Task Execution Role**: Select `ecsTaskExecutionRole`.
6.  **Container Details**:
    * **Image**: `<YOUR_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yt-digest:latest`
    * **Command**:
        ```bash
        sh,-c,aws s3 cp s3://ytdigest/queries.json . && python app.py && aws s3 cp feed.xml s3://ytdigest/feed.xml --content-type "application/rss+xml"
        ```
        *(Append ` --acl public-read` if using ACLs for public access).*
7.  **Environment Variables**:
    * `OPENAI_API_KEY`: `sk-...`
    * `PROXY_USERNAME`: `...`
    * `PROXY_PASSWORD`: `...`
    * `FEED_BASE_URL`: `https://ytdigest.s3.amazonaws.com/`

---

## Step 6: Schedule with EventBridge

1.  Go to **Amazon EventBridge** > **Schedules** > **Create Schedule**.
2.  **Schedule**: Cron-based (e.g., `0 7 * * ? *` for daily at 7 AM).
3.  **Target**: **Amazon ECS** > **Run Task**.
4.  **Target Configuration**:
    * **Cluster**: Select your Fargate cluster.
    * **Task Definition**: `yt-digest-rss` (LATEST).
    * **Compute options** (Crucial Step):
        * Expand this section.
        * Change **Launch type** from `EC2` to **`FARGATE`**.
    * **Configure network configuration**:
        * **Subnets**: Select **ALL** available subnets (Public).
        * **Auto-assign Public IP**: Change to **`ENABLED`**.
        * *Note: If Public IP is disabled, the task will fail silently because it cannot pull the Docker image.*

---

## Accessing Your Feed

Once the task runs successfully, your RSS feed will be available at:

* **Standard S3 URL**: `https://ytdigest.s3.amazonaws.com/feed.xml`