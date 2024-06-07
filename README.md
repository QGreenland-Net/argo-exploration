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


#### Check dashboard

```bash
kubectl -n argo port-forward service/argo-server 2746:2746
```


#### Real workflow

```bash
argo submit -n argo --watch workflows/seal-tags-csv.yml
```


## Medium workflow spike

We integrated a QGreenland workflow with a portion of the PDG visualization workflow.
The PDG vizualiation workflow steps are encapsulated as a
[WorkflowTemplate](https://argo-workflows.readthedocs.io/en/latest/workflow-templates/),
and the workflow references that template.

### WorkflowTemplate

This is a "building block" that's installed to the cluster. To install ours:

```bash
argo -n argo template create templates/viz.yml
```


### Workflow proper

The workflow itself is run as usual once the templates are installed:

```bash
argo -n argo submit --watch workflows/ice_basins_viz.yml
```


## Takeaways

* Generally impressed with user experience, polish, ease. Took 1 hour to build as small
  example end-to-end, starting from knowing nothing and Argo not installed, to
  finishing `workflows/seal-tag-csv.yml`.
* Submitting and watching jobs is an amazing UX compared to other tools we tested
* `argo logs @latest` :star_struck:


## Resources

* <https://github.com/akuity/awesome-argo>
