# Use the rocker/shiny-verse base image
FROM rocker/shiny-verse:latest

# Install system dependencies
FROM rocker/shiny-verse:latest

RUN apt-get update && apt-get install -y python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Force reticulate miniconda reinstall
RUN R -e "install.packages('reticulate')"
RUN R -e "reticulate::install_miniconda(force = TRUE)"

# Install reticulate and other R packages
RUN R -e "install.packages(c('shiny', 'reticulate', 'ggplot2', 'plotly', 'shinycssloaders'))"

# Create a directory for your app
RUN mkdir /srv/shiny-app

# Copy your app files into the container
COPY . /srv/shiny-app

# Set the working directory
WORKDIR /srv/shiny-app

# Install Python dependencies
ENV VIRTUALENV_NAME=shiny_env
RUN R -e "reticulate::virtualenv_create(Sys.getenv('VIRTUALENV_NAME'), python = '/usr/bin/python3')"
RUN bash -c "source /root/.virtualenvs/shiny_env/bin/activate && pip3 install setuptools"
RUN R -e "reticulate::virtualenv_install(Sys.getenv('VIRTUALENV_NAME'), requirements = 'requirements.txt', ignore_installed = TRUE)"

# Expose the port that Shiny uses
EXPOSE 3838

# Start the Shiny app
CMD ["R", "-e", "shiny::runApp('/srv/shiny-app/app.R', host = '0.0.0.0', port = 3838)"]