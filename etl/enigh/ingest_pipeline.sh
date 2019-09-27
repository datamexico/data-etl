bamboo-cli --folder . --entry enigh_jobs_pipeline
bamboo-cli --folder . --entry enigh_population_pipeline
bamboo-cli --folder . --entry enigh_population_pipeline

for i in $(seq -f "%02g" 2016 2018)
do
    bamboo-cli --folder . --entry enigh_jobs_pipeline --year="$i"
    bamboo-cli --folder . --entry enigh_population_pipeline --year="$i"
    bamboo-cli --folder . --entry enigh_population_pipeline --year="$i"

done