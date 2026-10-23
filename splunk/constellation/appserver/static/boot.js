require(['splunkjs/mvc/simplexml/ready!'], function () {
    var script = document.createElement('script');
    script.type = 'module';
    script.src = Splunk.util.make_url('/static/app/constellation/constellation.js');
    document.head.appendChild(script);
});
