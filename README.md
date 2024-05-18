# lazy-docker-build-push-action

Lazily build Docker images to content-identifying-hash based tags.

This aims to speed up build times by avoiding expensive rebuilding of
slow-moving layers, such as those containing external dependencies. While Docker
layer caching can achieve this in some cases, doing so requires storing and
loading the relevant caches which can prove almost as time consuming as
rebuilding the layers. This Action uses stable hashing of inputs to achieve
speed-ups without full caching.

The actual Docker build is handled by [`docker/build-push-action`][docker-bpa]
and the majority of the action's arguments are passed directly to that action.

The following are automatically included in the identifying hash:

* Annotations
* Build args
* Build contexts
* Build target
* Build ulimit
* Labels
* the Dockerfile itself (no attempt is made to parse it)

Any other inputs (including e.g: files referenced in `COPY` statements) **must
be specified manually**.

Tags for the built image are inferred automatically from those passed. For each
input tag, the image name is extracted and a tag name of the form
`content-hash-<hash>` is appended, so `user/app:latest` would additionally be
tagged as `user/app:content-hash-1234abc...`.

Hashes are stable for given inputs when using a pinned version of this Action.
Counterexamples to this are considered bugs. While effort will be made to
maintain hash stability, new releases may include changes to the hash. Since
this Action is in effect a cache, such changes will not be considered breaking.

Arguments:

* `tags` (required): A list of image names (`user/app`) or full tags
  (`user/app:latest`) to apply to the resulting image. Passed through to
  `docker/build-push-action` with the content-identifying tags applied.

* `pull` or `load`: If either of these are set to `true` then any existing image
  matching the computed hash will be made available locally. Otherwise the
  action will attempt to avoid fetching images unless a build is needed.

  **TODO**: implement this.

* `extra-inputs` (optional): A list of globs of files to include in the content
  hash.

Other arguments to `docker/build-push-action` are passed through unchanged.

Outputs:

* `image-name`: The name of the image (e.g: `user/app`), reflected from the
  parsed `tags` input for convenience. Where several names are encountered, this
  is the first from the list for which the desired image (now) exists.

  **TODO**: implement handling for one of the names not existing

* `image-tag`: The tag of the image (e.g: `content-hash-1234abc...`), as
  constructed from the hashed inputs.

* `image-name-tag`: The full name of the image, `<image-name>:<image-tag>` (e.g:
  `user/app:content-hash-1234abc...`), for convenience.

* `tag-existed`: Whether or not the tag already existed (for any of the input
  names) and thus whether or not a build occurred.

Example usage:

```yaml
on:
  push:
    branches:
      - main

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build base layer
        uses: PeterJCLaw/docker-hashed-build-push-action@v0.1
        id: build-base
        with:
          context: .
          push: true
          tags: user/base:latest
          extra-inputs: requirements*.txt

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: user/app:latest
          build-args: |
            BASE_IMAGE=${{ steps.build-base.outputs.image-name-tag }}
```

[docker-bpa]: https://github.com/marketplace/actions/build-and-push-docker-images
