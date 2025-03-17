# cryptoArbBot

A simulator bot for arbitrage trading of cryptos.

## App

1.  **Install Docker Desktop:** (if not already installed)
    * Download and install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop).

2.  **Open Terminal and Log in to Docker Hub:**
    * Open your terminal or command prompt.
    * Execute the following command and enter your Docker Hub credentials:
        ```bash
        docker login
        ```

3.  **Pull the Docker Image:**
    * Download the `cryptoArbBot` image from Docker Hub:
        ```bash
        docker pull ces0491/fse:latest
        ```

4.  **Run the Docker Container:**
    * Start the application container, mapping port 3838:
        ```bash
        docker run -p 3838:3838 ces0491/fse:latest
        ```

5.  **Access the Application in a Browser:**
    * Open your web browser.
    * Enter the following address:
        ```
        http://localhost:3838
        ```
