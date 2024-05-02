# argo spike

## Setup

### Argo CLI

<https://argo-workflows.readthedocs.io/en/latest/walk-through/argo-cli/>


### Follow the quickstart (dev) instructions

<https://argo-workflows.readthedocs.io/en/latest/quick-start/>

#### Install Argo

```bash
kubectl create namespace argo
kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.6/quick-start-minimal.yaml
```


#### Hello world

```bash
argo submit -n argo --watch https://raw.githubusercontent.com/argoproj/argo-workflows/main/examples/hello-world.yaml
```


#### Checked dashboard

```bash
kubectl -n argo port-forward service/argo-server 2746:2746
```





## Resources

* <https://github.com/akuity/awesome-argo>
