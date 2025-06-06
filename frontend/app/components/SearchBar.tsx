import { Globe, Link, Mic, Search, Activity } from 'lucide-react';

export default function SearchBar() {
  return (
    <div className="w-full max-w-xl mx-auto">
      <div className="flex items-center bg-[#232425] rounded-2xl px-6 py-4 shadow-lg">
        <input
          className="flex-1 bg-transparent outline-none text-white text-lg placeholder-gray-400"
          placeholder="Ask anything..."
        />
        {/* Search Button */}
        <button className="ml-2 bg-[#1BA1F9] p-3 rounded-lg flex items-center justify-center">
          <Search className="w-5 h-5 text-white" />
        </button>
        {/* Other icons */}
        <div className="flex items-center ml-4 space-x-4">
          <Globe className="w-5 h-5 text-gray-400" />
          <Link className="w-5 h-5 text-gray-400" />
          <Mic className="w-5 h-5 text-gray-400" />
          <Activity className="w-5 h-5 text-[#1BA1F9]" />
        </div>
      </div>
    </div>
  );
} 