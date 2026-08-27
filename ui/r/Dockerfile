FROM rocker/shiny:latest

USER root

RUN apt-get update \
    && apt-get install -y \
        --no-install-recommends \
        libcurl4-openssl-dev \
        libssl-dev \
        libxml2-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN R -e "install.packages( \
    c( \
        'shiny', \
        'shinydashboard', \
        'jsonlite', \
        'ggplot2', \
        'dplyr', \
        'DT', \
        'scales', \
        'lubridate', \
        'tidyr' \
    ), \
    repos='https://cloud.r-project.org' \
)"

RUN rm -rf /srv/shiny-server/*

COPY app.R /srv/shiny-server/app.R
COPY www /srv/shiny-server/www

EXPOSE 3838

CMD ["/usr/bin/shiny-server"]