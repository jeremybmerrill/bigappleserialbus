// "use strict";

$(function(){
  // TODO: suggest based on http://bustime.mta.info/api/where/stops-for-location.json?lat=40.748433&lon=-73.985656&latSpan=0.005&lonSpan=0.005&key=YOUR_KEY_HERE

  getRoutes = function(){
    $.getJSON("/buses", function(routes){
      // [["MTA NYCT_B65", "B65", "Downtown Brooklyn - Crown Heights", "via Bergen St & Dean St"]...]
      var bloodhoundRoutes = _(routes).map(function(route){ 
        return {
            val: route[1] + ", " + route[2] + ", " + route[3], 
            id: route[0],
          }; 
        });
      var routesEngine = new Bloodhound({
        name: 'routes',
        local: bloodhoundRoutes,
        datumTokenizer: function(d) {
          return Bloodhound.tokenizers.whitespace(d.val);
        },
        datumTokenizer: Bloodhound.tokenizers.obj.whitespace('val'),
        queryTokenizer: Bloodhound.tokenizers.whitespace
      });  
      routesEngine.initialize();

      $('#routeDescription').typeahead({
        minLength: 2,
        highlight: true,
      },
      {
        name: 'routes',
        displayKey: 'val',
        source: routesEngine.ttAdapter()
      });
    });
  }
  getDestinations = function(route_id, cb){
    $.getJSON("/buses/" + route_id, cb);
  }
  getStops = function(route_id, direction_id, cb){
    $.getJSON("/buses/" + route_id + "/" + direction_id, function(stops){

      var bloodhoundStops = _(_(stops).keys()).map(function(stop){ 
        return {
            val: stop + " (" + stops[stop] + ")", 
            id: stops[stop],
          }; 
        });
      var stopsEngine = new Bloodhound({
        name: 'stops',
        local: bloodhoundStops,
        datumTokenizer: function(datum){ return datum.val.split(/[ \/]/) },
        queryTokenizer: Bloodhound.tokenizers.whitespace
      });  
      stopsEngine.initialize();

      if(cb)
        cb(stops, stopsEngine);
    });
  }

  postprocess = function(bus){
    bus.destination = $('#destination').find('option:selected').text();
    return bus;
  }

  getCurrentItems = function(){
    $.getJSON("/config", function(configItems){
      configItems = _(configItems["stops"]).map(preprocessConfigItems);
      $('#buses').list({
        items: configItems,
        templateEngine: function (t) { return _.template(t, {}) }
      }).removeClass('hide');

      $('.list-item.bus .edit').on('click', function(){ $('#form-modal').modal('show'); });
      $('#bus-form').on('submitted.ac.form', function(e) {
        $.post("/buses", postprocess(e.object), function(){ window.location.reload() } );
      });

      $('.bus-delete').off('click').on('click', deleteBus);
    })
  };

  deleteBus = function(e){
    console.log(e);
    var index = $('.bus').index($(e.currentTarget).parents('.bus'));
    console.log(index);
    $.ajax({
      url: 'buses/' + index, 
      method: 'DELETE',
      success: function(){ window.location.reload() }
    });
  }

  preprocessConfigItems = function(item, index){
    item.destination = item.destination || "Destination TK";
    item.destinationId = item.destinationId || "1";
    item.routeDescription = item.routeDescription || '';
    getRouteInfo(item, index);
    return item;
  }

  getRouteInfo = function(i, index){
    $.getJSON('/businfo/MTA%20NYCT_' + i.route_name.toUpperCase() + "/" + i.stop, function(resp){
      $('#buses').list('update', index, _.extend(i, resp));
      $('.bus-delete').off('click').on('click', deleteBus);
    })
  }

  clearDirections = function(){
    $('#destination').children().each(function(i, el){
      if(i>0){
        $(el).remove();
      }
    });
  }
  clearStops = function(){

  }


  getCurrentItems();
  getRoutes();
  $('#routeDescription').on('typeahead:selected', function(e, routeSuggestion){
    var routeId = routeSuggestion.id;
    $('#routeName').val(routeId);

    // remove directions (and TODO: stops) that pertain to another route.
    clearStops();
    clearDirections();


    getDestinations(routeId, function(destinations){
      $('#destination').removeAttr('disabled');
      _(_(destinations).keys()).each(function(name){
        var opt = "<option value='"+destinations[name]+"'>"+name+"</option>";
        $('#destination').append(opt);
      });

      $('#destination').on('change', function(e){
        var destinationId =  $('#destination').val();
        $('#destinationId').val( destinationId);
        clearStops();
        if($('#destination').val().length){ // don't do this if the "selected" option is the placeholder
          $('#stopName').removeAttr('disabled');
          getStops(routeId, destinationId, function(stops, stopsEngine){
            $('#stopName').typeahead({
              minLength: 2,
              highlight: true,
            },
            {
              name: 'stops',
              displayKey: 'val',
              source: stopsEngine.ttAdapter()
            });
            $('#stopName').on('typeahead:selected', function(e, stopSuggestion){
              $('#stop').val( stopSuggestion.id );
            });
          })
        }
      })
    })
  })


});