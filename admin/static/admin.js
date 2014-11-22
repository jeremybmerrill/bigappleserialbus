$(function(){


  getBusStops =  function(){
    $.get("http://bustime.mta.info/api/where/routes-for-agency/MTA%20NYCT.xml?key=" + window.API_KEY, function(bus_routes){
      console.log(bus_routes);
      
    })
  },
  getAPIKey = function(cb){
    $.get("/apikey").done(function(apikey){
      window.API_KEY = apikey;
      if(cb)
        cb(apikey)
    })
  }

  getAPIKey(getBusStops);
});