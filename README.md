# Static Lineage OTA updater
A simple way of generating the necessary json content to serve it to the Lineage OS updater using a simple file based HTTPS server.

## Introduction
The main requirement for an official Lineage OS release for any device is a kernel in source code format. So this means that many devices won't get a Lineage OS release simply because there is no source code provided by the manufacturer either because they are lazy or they aren't allowed to as it is the case with Mediatek. So for any hobby developer the only possible way to provide the Lineage experience on any such devices is by offering an *unofficial* release. This also means no official OTA updates. Thankfully the Lineage OS team provided a solution:

The Lineage OS updater is nothing more than a simple file download service. It uses the information provided in json format to download the required files. There are some implementations out there in the wild which use a [dynamic approach](https://github.com/ADeadTrousers/LineageOTA) but that means one needs to *own* and *pay* for webspace to just serve a simple json file.

So here comes my static approach. Simply put I just use everything Github offers for free (project releases and static webpages) to provide everything needed for the Lineage OTA updater to work.

## How to use it (simple)
If you want to use this for your own device do the following:
1. Fork this repo.
2. Make the new repo [available on `github.io`](https://pages.github.com/)
3. Clone it onto your local PC.
4. Modify `github.json` to point to your devices repo.
5. Set the property `lineage.updater` in your `build.prop` to your new repo.
6. Run `update.sh` (Linux) or `update.cmd` (Windows) and commit the changes back onto the repo.
7. Repeat step 6 whenever you have created a new release.

## Requirements

### Local setup
As you are quite obviously already building Lineage OS on your local machine I won't go into the details of how to setup git or python for that matter. You just need to add three more modules to python and then you are good to go. Just run the following commands either from your command prompt (Windows) or your terminal (Linux):
```bash
pip install pyparsing
pip install packaging
pip install pathvalidate
```

### Device setup
In order to integrate this in your LineageOS based ROM, you need to add the [`lineage.updater.uri`](https://github.com/LineageOS/android_packages_apps_Updater/blob/lineage-15.0/src/org/lineageos/updater/misc/Constants.java#L39) property in your `build.prop` file:
```properties
# ...
lineage.updater.uri=https://username.github.io/LineageOTAstatic/api/v1/{device}_{type}
# ...
```

### Release setup
For your devices Github release you need to publish the following files:
- `lineage-{version}-{timestamp}-UNOFFICIAL-{model}.zip`
- `build.prop` taken from `system` folder of your `out/target/product`.
- `build.md5sum` containing at least one line with the md5 of the zip file. Best to use a similar command like:
```bash
md5sum lineage-{version}-{timestamp}-UNOFFICIAL-{model}.zip > build.md5sum
```

## Technical informations

### Structure of the generated json file
```json
[
    {
        "incremental": "Identification of the build; ro.build.version.incremental",
        "api_level": "The api of underlying andorid; ro.build.version.sdk",
        "url": "Url that points to the release zip file",
        "timestamp": Timesatmp_of_the_release,
        "md5sum": "The md5 hash of the release zip file",
        "changes": "Url that points to the changelog of the rleases",
        "channel": "The channel this release is built upon; ro.lineage.releasetype",
        "filename": "Filename of to zip file",
        "romtype": "The channel this release is built upon; ro.lineage.releasetype",
        "datetime": Timesatmp_of_the_release,
        "version": "The version of the lineage release; ro.lineage.build.version",
        "id": "An unique identifier for this release",
        "size": The_size_of_the_zip_file
    }
]
```

### Possible placeholders
As of [5252d60](https://github.com/LineageOS/android_packages_apps_Updater/commit/5252d606716c3f8d81617babc1293c122359a94d) these placeholders are replaced at runtime: 
>   {device} - Device name
>
>   {type} - Build type
>
>   {incr} - Incremental version

### Github api calls and rate limitation
As [Github limited the rate for their api calls](https://docs.github.com/en/developers/apps/building-github-apps/rate-limits-for-github-apps) I included a simple buffering algorithm to ensure that during testing one would not exceed the limit. When there are buffered files available you will be asked if you want to update them. So if you want to update for your latest release simply pick [Y]es as your answer.

## Extension for other file hosters
As of now this is a very basic script which only offers Github as the file hosting service. I know there are many others out there in the wild but I neither have the time nor the will to support each and everyone. So if you want it for your own file hoster you need to adapt the script yourself. It's not that complicated and if you think your changes will make a good addition to this project simply create a pull request and I'll look into it.
