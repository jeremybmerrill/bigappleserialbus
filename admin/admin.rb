require 'sinatra'
require "sinatra/reloader" if development?
require 'nokogiri'
require 'net/http'
require 'json'
require 'yaml'

set :public_folder, File.join(File.dirname(__FILE__), 'static')

APIPATH = File.join(File.dirname(__FILE__), '..', 'apikey.txt' )
CONFIG_PATH = File.join(File.dirname(__FILE__), '..', 'config.yaml' )

APIKEY = open(APIPATH, 'r').read.strip

open(CONFIG_PATH, 'r') do |f|
  $config = YAML.load f.read
end

#TODO: stash these things for a few days on the hard drive

def getRoutes
  # [["MTA NYCT_B65", "B65", "Downtown Brooklyn - Crown Heights", "via Bergen St & Dean St"]...]
  xml_str = Net::HTTP.get URI("http://bustime.mta.info/api/where/routes-for-agency/MTA%20NYCT.xml?key=#{APIKEY}")
  xml = Nokogiri::XML(xml_str)
  xml.css("response data list route").to_a.map{|rte| [rte.css('id').text, rte.css('shortName').text, rte.css('longName').text, rte.css('description').text]}
end

def getDestinations(route_id)
  # [["CROWN HTS RALPH AV", 0], ["DNTWN BKLYN FULTON MALL", 1]] -- hashified.
  json = Net::HTTP.get URI("http://bustime.mta.info/api/where/stops-for-route/#{URI::encode(route_id)}.json?key=#{APIKEY}&includePolylines=false&version=2")
  route_info = JSON.load(json)
  puts route_info["data"]["entry"]["stopGroupings"][0]["stopGroups"]
  directions = route_info["data"]["entry"]["stopGroupings"][0]["stopGroups"].map{|dir| [dir["name"]["name"], dir["id"]] }

  Hash[*directions.flatten]
end

def getStops(route_id, direction_id)
  json = Net::HTTP.get URI("http://bustime.mta.info/api/where/stops-for-route/#{URI::encode(route_id)}.json?key=#{APIKEY}&includePolylines=false&version=2")
  route_info = JSON.load(json)
  direction = route_info["data"]["entry"]["stopGroupings"][0]["stopGroups"].find{|dir| dir["id"] == direction_id}
  stop_ids = direction["stopIds"]

  refs = stop_ids.map{|stop_id| route_info["data"]["references"]["stops"].find{|ref| ref["id"] == stop_id } }
  Hash[*refs.map{|ref| [ref["name"], ref["id"]]}.flatten]
end

def write_config!
  open(CONFIG_PATH, 'w') do |f|
    f << YAML.dump($config)
  end
end

def pickPins

end

def createYamlEntry(params)
  {
    "route_name" => params["route_name"][9..-1].downcase, # "MTA NYCT_B65" => "b65"
    "stop" => params["stop"],
    "distance" => params["distance"],
    "redPin" => params["redPin"],
    "greenPin" => params["greenPin"],
    "direction" => params["destinationId"],
    "terminus" => params["destination"],
    "stopName" => params["stopName"],
    "routeDescription" => params["routeDescription"]
  }
end

get '/' do
  redirect to("index.html")
end

get '/apikey' do
  APIKEY
end

get '/buses' do 
  JSON.dump getRoutes
end

get '/buses/:id' do
  JSON.dump getDestinations(params[:id])
end

get '/buses/:routeId/:directionId' do
  JSON.dump getStops(params[:routeId], params[:directionId])
end

get '/config' do
  JSON.dump $config
end

delete '/buses/:id' do 
  $config["stops"].delete_at(params[:id].to_i)
  write_config!
  ''
end

post '/buses' do 
  $config["stops"].reject!{|i| i["route_name"] == params[:route_name] && i["stop"] == params["stopId"]}
  $config["stops"] << createYamlEntry(params)
  write_config!
  ''
end