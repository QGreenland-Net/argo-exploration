# argo spike

Exploratory repo for evaluating the use of Argo Workflows as the orchestrator
for OGDC recipes.

The QGreenland-Net team decided to move forward with the use of argo for the
OGDC. See the [ogdc-runner](https://github.com/QGreenland-Net/ogdc-runner/)
repository for the lastest developments.

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


#### Check dashboard

```bash
kubectl -n argo port-forward service/argo-server 2746:2746
```


#### Real workflow

```bash
argo submit -n argo --watch workflows/seal-tag-csv.yml
```


## Takeaways

* Generally impressed with user experience, polish, ease. Took 1 hour to build
  end-to-end, starting from knowing nothing and Argo not installed, to finishing our
  seal tags example.
* Submitting and watching jobs is amazing
* `argo logs @latest` :star_struck:
* Next step: dependencies, >1 processing step


## Resources

* <https://github.com/akuity/awesome-argo>

#### NOTE:  

This is an exploratory repository so not everything is expected to work perfectly. The medium-workflow and lessons learned will be moved into [ogdc-runner](https://github.com/QGreenland-Net/ogdc-runner) and [ogdc-recipes](https://github.com/QGreenland-Net/ogdc-recipes). Additionally, helm of the workflow is [here](https://github.com/rushirajnenuji/dataone-gse/blob/feature-argo-helm/scripts/workflows/ice_basins_workflow.py).
