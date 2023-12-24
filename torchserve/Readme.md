# torchserve


Deployment locally and with docker

## :rocket: Deployment

In order to deploy the model you will need to reproduce the following steps once you installed all the requirements
as described in the section above.

### 1. Generate MAR file

First of all you will need to generate the MAR file, which is the "ready to serve" archive of the model
generated with `torch-model-archiver`. So on, in order to do so, you will need to use the following command:

```bash
torch-model-archiver --model-name foodnet_resnet18 \
                     --version 1.0 \
                     --model-file model/model.py \
                     --serialized-file model/foodnet_resnet18.pth \
                     --handler model/handler.py \
                     --extra-files model/index_to_name.json
```

So __torch-model-archiver__'s used flags stand for:

- `--model-name`: name that the generated MAR "ready to serve" file will have.
- `--version`: it's optional even though it's a nice practice to include the version of the models 
so as to keep a proper tracking over them.
- `--model-file`: file where the model architecture is defined.
- `--serialized-file`: the dumped state_dict of the trained model weights.
- `--handler`: the Python file which defines the data preprocessing, inference and postprocessing.
- `--extra-files`: as this is a classification problem you can include the dictionary/json containing 
the relationships between the IDs (model's target) and the labels/names and/or also additional files 
required by the model-file to format the output data in a cleaner way.

__Note__: you can define custom handlers, but you don't need to as there are already some default handlers
per every possible problem defined by TorchServe and accessible through a simple string. The current possible 
default handlers are: "image_classifier", "image_segmenter", "object_detector" and "text_classifier". You can 
find more information at [TorchServe Default Handlers](https://pytorch.org/serve/default_handlers.html)

Once generated you will need to place the MAR file into the `deployment/model-store` directory as it follows:

```bash
mv foodnet_resnet18.mar deployment/model-store/
```

More information regarding `torch-model-archiver` available at 
[Torch Model Archiver for TorchServe](https://github.com/pytorch/serve/blob/master/model-archiver/README.md).

### 2. Deploy TorchServe

Once you create the MAR \ model, you just need to serve it. The serving process
of a pre-trained PyTorch model as a MAR file, starts with the deployment of the TorchServe REST APIs, which are the
Inference API, Management API and Metrics API, deployed by default on `localhost` (of if you prefer `127.0.0.1`) in the
ports 8080, 8081 and 8082, respectively. While deploying TorchServe, you can also specify the directory where the MAR files
are stored, so that they are deployed within the API at startup.

So on, the command to deploy the current MAR model stored under `deployment/model-store/` is the following:

```bash
torchserve --start \
           --ncs \
           --ts-config deployment/config.properties \
           --model-store deployment/model-store \
           --models foodnet=foodnet_resnet18.mar
```

So __torchserve__'s used flags stand for:

- `--start`: means that you want to start the TorchServe service (deploy the APIs).
- `--ncs`: means that you want to disable the snapshot feature (optional).
- `--ts-config`: to include the configuration file which is something optional too.
- `--model-store`: is the directory where the MAR files are stored. 
- `--models`: is(are) the name(s) of the model(s) that will be served on the startup, including both an alias 
which will be the API endpoint of that concrete model and the filename of that model, with format `endpoint=model_name.mar`.

__Note__: another procedure can be deploying TorchServe first (without defining the models), then registering the model using
the Management API and then scaling the number of workers (if needed).

```bash
torchserve --start --ncs --ts-config deployment/config.properties --model-store deployment/model-store
curl -X POST "http://localhost:8081/models?initial_workers=1&synchronous=true&url=foodnet_resnet18.mar"
curl -X PUT "http://localhost:8081/models/foodnet?min_worker=3"
```

More information regarding `torchserve` available at [TorchServe CLI](https://pytorch.org/serve/server.html#command-line-interface).

### 3. Check its status

In order to check the availability of the deployed TorchServe API, you can just send a HTTP GET
request to the Inference API deployed by default in the `8080` port, but you should check the `config.properties` file, which
specifies `inference_address` including the port.

```bash
curl http://localhost:8080/ping
```

If everything goes as expected, it should output the following response:

```json
{
  "status": "Healthy"
}
```

__Note__: If the status of the health-check request was `"Unhealthy"`, you should check the logs either from the console from where
you did run the TorchServe deployment or from the `logs/` directory that is created automatically while deploying TorchServe from
the same directory where you deployed it.

### 4. Stop TorchServe

Once you are done and you no longer need TorchServe, you can gracefully shut it down with the
following command:
  
```bash
torchserve --stop
```

Then the next time you deploy TorchServe, it will take less time than the first one if the models to be server were already
registered/loaded, as TorchServe keeps them cached under a `/tmp` directory so it won't need to load them again if neither the name nor 
the version changed. On the other hand, if you register a new model, TorchServe will have to load it and it may take a little 
bit more of time depending on your machine specs. 

---

## :whale2: Docker

In order to reproduce the TorchServe deployment in an Ubuntu Docker image, you should just use the following set of commands:

```bash
docker build -t ubuntu-torchserve:latest deployment/
docker run --rm --name torchserve_docker \
           -p8080:8080 -p8081:8081 -p8082:8082 \
           ubuntu-torchserve:latest \
           torchserve --model-store /home/model-server/model-store/ --models foodnet=foodnet_resnet18.mar
```

For more information regarding the Docker deployment, you should check TorchServe's 
explanation and notes available at [pytorch/serve/docker](https://github.com/pytorch/serve/tree/master/docker), 
as it also explains how to use their Docker image (instead of a clear Ubuntu one) and
some tips regarding the production deployment of the models using TorchServe.

---


References

1. https://github.com/alvarobartt/serving-pytorch-models/tree/main 
2. https://towardsdatascience.com/serving-pytorch-models-with-torchserve-6b8e8cbdb632
3. https://github.com/pytorch/serve/blob/master/examples/image_classifier/mnist/README.md
4. https://github.com/pytorch/serve/blob/master/examples/image_classifier/mnist/Docker.md
5. https://rpadovani.com/pytorch-docker-image
6. https://docs.vultr.com/deploy-a-machine-learning-model-to-production-using-torchserve
7. https://blog.pulze.ai/moving-from-lab-to-production-deploying-prompt-classification-models-with-torchserve/
8. 